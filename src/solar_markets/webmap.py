"""Step 6: interactive web map of the layers, with sector details, search and a first-visit guide.

Inputs:  outputs/solar_share_calibrated.tif, outputs/grid_share_pred.tif,
         data/processed/feature_stack.tif, labels.gpkg, train_table.csv,
         reports/shap_values.csv, reports/calibration.json
Outputs: data/processed/sector_summary.gpkg   labels + predictions + top drivers per sector
         reports/top_underserved_sectors.csv  ranked list (field-check shortlist)
         docs/map.html                        the map (GitHub Pages), one self-contained file
Owner:   D (docs, map & pitch); see Part 12 of the team playbook.

    python -m solar_markets.webmap --config config.yml
    python -m solar_markets.webmap --from-map    # rebuild docs/map.html from the data already in it

`--from-map` needs no data/processed: after a change to the template or the layer wording it
re-renders the page around the rasters and sector numbers the last full run embedded.

The page is a Leaflet map built from `webmap_template.html`, with every layer, legend and sector
record embedded as JSON. One layer is shown at a time (results first, then the six clues the
model uses), and its legend, highlighted sectors and the details of a clicked sector follow it,
so every priority zone can be traced back to its inputs.
"""

from __future__ import annotations

import base64
import io
import json
import math
import re
from html import escape
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import yaml

from solar_markets.config import cli_args, get_paths, load_config
from solar_markets.export import normalise, unserved_households
from solar_markets.features import KM_PER_DEG, Grid, area_zones, zone_means

FEATURE_LABELS = {
    "ntl": "night lights",
    "pop": "population density",
    "travel_min": "travel time to a city",
    "built": "built-up area",
    "rwi": "wealth (RWI)",
    "dist_grid": "distance to the grid",
}
TOP_N = 10
TEMPLATE = Path(__file__).with_name("webmap_template.html")
REPO = "https://github.com/PAZZO123/oseas26-solar-markets-sales-data"
LINKS = {"repo": REPO, "limitations": f"{REPO}/blob/main/LIMITATIONS.md",
         "user_gaps": f"{REPO}/blob/main/docs/user-gaps.md"}

# Background maps. Esri's tiles also load when map.html is opened as a local file;
# OpenStreetMap's servers refuse requests without a website address, so it is not used.
ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services"
BASEMAPS = {
    "grey": {"name": "Grey", "url": f"{ESRI}/Canvas/World_Light_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}",
             "labels": f"{ESRI}/Canvas/World_Light_Gray_Reference/MapServer/tile/{{z}}/{{y}}/{{x}}",
             "attribution": "Tiles &copy; Esri &mdash; Esri, HERE, Garmin, OpenStreetMap contributors"},
    "satellite": {"name": "Satellite", "url": f"{ESRI}/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}",
                  "labels": f"{ESRI}/Reference/World_Boundaries_and_Places/MapServer/tile/{{z}}/{{y}}/{{x}}",
                  "attribution": "Imagery &copy; Esri, Maxar, Earthstar Geographics"},
}

# The layers people can show, in menu order. `metric` is the sector field the details card leads
# with; `format` says how to print it (see fmt()). `colour_note` names the colour at the high end
# of the ramp (not every ramp gets darker as values rise); `table_unit` labels the sector value.
LAYERS = [
    {"key": "underserved", "group": "Results", "name": "Underserved market",
     "short": "Households with neither grid nor solar",
     "description": "Estimated households per km² that light their homes with neither grid "
                    "electricity nor solar. Darker = more families without light. This is the "
                    "layer funders act on.",
     "cmap": "magma_r", "log": False, "unit": "households per km²", "format": "int",
     "metric": "unserved_hh", "metric_label": "households with neither grid nor solar",
     "colour_note": "darker = more households without light", "table_unit": "homes in this sector"},
    {"key": "route", "group": "Results", "name": "Who should serve them", "kind": "sectors",
     "short": "Grid, a working solar market, or none yet",
     "description": "Who could bring light to each sector's unlit homes: the grid company where "
                    "homes are on or near the grid, solar companies where their market already "
                    "works, and funders where the solar market has not arrived.",
     "unit": "per sector", "format": "int",
     "metric": "unserved_hh", "metric_label": "households with neither grid nor solar",
     "colour_note": "each colour is one route, see the key", "table_unit": "homes in this sector"},
    {"key": "penetration", "group": "Results", "name": "Solar penetration",
     "short": "Share of homes lit by solar",
     "description": "Estimated share of households whose main light is solar (calibrated to the "
                    "2022 census). Blank where almost nobody lives.",
     "cmap": "viridis", "log": False, "unit": "of households", "format": "pct",
     "metric": "pred_solar", "metric_label": "of households use solar (model estimate)",
     "colour_note": "yellow = more solar, dark purple = little solar", "table_unit": "of homes"},
    {"key": "ntl", "group": "Clues the model uses", "name": "Night lights",
     "short": "Brightness at night (VIIRS 2022)",
     "description": "Average night-time brightness seen by satellite. Bright = grid electricity "
                    "and towns. Solar lamps are too dim to show, which is why the model needs "
                    "other clues.",
     "cmap": "inferno", "log": True, "unit": "nW/cm²/sr", "format": "num2",
     "metric": "ntl", "metric_label": "night-light brightness where people live",
     "colour_note": "yellow = brighter, black = dark", "table_unit": "nW/cm²/sr"},
    {"key": "pop", "group": "Clues the model uses", "name": "Population",
     "short": "People per km² (WorldPop 2020)",
     "description": "How many people live in each square kilometre. More people means more "
                    "potential customers and more need.",
     "cmap": "YlGnBu", "log": True, "unit": "people per km²", "format": "int",
     "metric": "density", "metric_label": "people per km² on average",
     "colour_note": "darker blue = more people", "table_unit": "people per km²"},
    {"key": "rwi", "group": "Clues the model uses", "name": "Wealth",
     "short": "Relative Wealth Index (Meta)",
     "description": "Estimated wealth compared with the rest of Rwanda, from about -1 (poorer) "
                    "to +2 (richer). Wealthier areas can afford solar more easily.",
     "cmap": "PuOr", "log": False, "unit": "index", "format": "num2",
     "metric": "rwi", "metric_label": "wealth index where people live",
     "colour_note": "purple = richer, brown = poorer", "table_unit": "index, 0 = middle"},
    {"key": "dist_grid", "group": "Clues the model uses", "name": "Distance to the grid",
     "short": "Km to the nearest power line (Gridfinder)",
     "description": "Distance to the nearest likely power line. Close to the grid, families "
                    "usually connect to it; far away, solar or nothing.",
     "cmap": "YlOrBr", "log": False, "unit": "km", "format": "num1",
     "metric": "dist_grid", "metric_label": "km to the grid where people live",
     "colour_note": "darker = farther from the grid", "table_unit": "km"},
    {"key": "travel_min", "group": "Clues the model uses", "name": "Travel time to a city",
     "short": "Minutes to the nearest city (2015)",
     "description": "Travel time to the nearest city of 50,000 or more people. Remote places "
                    "are harder for solar sales agents to reach.",
     "cmap": "BuPu", "log": False, "unit": "minutes", "format": "int",
     "metric": "travel_min", "metric_label": "minutes to a city where people live",
     "colour_note": "darker = more remote", "table_unit": "minutes"},
    {"key": "built", "group": "Clues the model uses", "name": "Built-up area",
     "short": "Share of land with buildings (ESA 2021)",
     "description": "Share of each square covered by buildings. High in towns, very low in "
                    "scattered rural settlements.",
     "cmap": "OrRd", "log": False, "unit": "of land", "format": "pct",
     "metric": "built", "metric_label": "of land built up where people live",
     "colour_note": "darker = more built-up", "table_unit": "of land"},
]
# The fields of a LAYERS entry the page uses; the rest of a page layer is its raster and legend.
# A layer of kind "sectors" has no raster: the page colours the sector shapes instead.
LAYER_TEXT = ("key", "group", "name", "short", "description", "unit", "format", "metric",
              "metric_label", "colour_note", "table_unit")
LAYER_RASTER = ("image", "stops", "ticks")

# Who could bring light to a sector's unlit homes; the rule is delivery_routes() with the
# thresholds in config.yml (webmap.routes). Colours match the page's grid / solar / neither.
ROUTES = [
    {"key": "grid", "name": "Grid connections", "short": "Grid", "who": "REG / EDCL",
     "colour": "#2f6690",
     "description": "Most homes already use the grid, or people live close to a line: connecting "
                    "the rest is the utility's job."},
    {"key": "solar_grow", "name": "Solar market working", "short": "Solar working",
     "who": "Solar and PAYGo companies",
     "colour": "#e8a33d",
     "description": "Solar already lights at least the national share of homes: companies sell "
                    "here and can reach more homes."},
    {"key": "solar_gap", "name": "Solar market not yet arrived", "short": "Solar not arrived",
     "who": "Funders: results-based financing, grants, new distributors", "colour": "#8a2846",
     "description": "Off the grid and little solar: the market has not reached these homes "
                    "without support."},
]


# ---------------------------------------------------------------- sector summary

def zone_sums(zones: np.ndarray, n_zones: int, values: np.ndarray) -> np.ndarray:
    ok = (zones >= 0) & np.isfinite(values)
    return np.bincount(zones[ok], weights=values[ok], minlength=n_zones)


def top_drivers(shap: pd.DataFrame, values: pd.DataFrame, features: list[str], n: int = 3
                ) -> pd.Series:
    """Text like "low night lights (+4.1 pp); far ..." from per-area SHAP values.

    "low" / "high" compares the area's feature value with the median over all areas; the
    number is the feature's push on the predicted solar share, in percentage points.
    """
    medians = values[features].median()
    out = {}
    for area_id, row in shap.set_index("area_id")[features].iterrows():
        parts = []
        for f in row.abs().sort_values(ascending=False).index[:n]:
            level = "high" if values.at[area_id, f] >= medians[f] else "low"
            parts.append(f"{level} {FEATURE_LABELS.get(f, f)} ({100 * row[f]:+.1f} pp)")
        out[area_id] = "; ".join(parts)
    return pd.Series(out, name="top_drivers")


def delivery_routes(props: pd.DataFrame, national_solar: float, rules: dict) -> pd.Series:
    """"grid", "solar_grow" or "solar_gap" per sector (see ROUTES).

    A sector is a grid job when at least `grid_share_min` of its homes use the grid or people
    live within `grid_km_max` of a line on average. Otherwise its solar market is working when
    the solar share reaches `solar_share_min` (the national share when that is null), and has not
    arrived below it. Census shares lead; the model's estimate fills in where the census has none.
    """
    grid = props["census_grid"].astype(float).fillna(props["pred_grid"])
    solar = props["census_solar"].astype(float).fillna(props["pred_solar"])
    solar_min = rules.get("solar_share_min") or national_solar
    near = (grid >= rules["grid_share_min"]) | (props["dist_grid"] <= rules["grid_km_max"])
    route = np.where(near, "grid", np.where(solar >= solar_min, "solar_grow", "solar_gap"))
    return pd.Series(route, index=props.index, name="route")


def share_ranks(props: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Share of households with neither grid nor solar per sector, and its rank (1 = highest).

    Ranking by share instead of number lets small, remote sectors where most homes are dark
    come up; ties go to the sector with more such homes.
    """
    share = (props["unserved_hh"] / props["households"].where(props["households"] > 0)).rename(
        "unserved_share")
    order = pd.DataFrame({"share": share, "hh": props["unserved_hh"]}).sort_values(
        ["share", "hh"], ascending=False, na_position="last").index
    rank = pd.Series(np.arange(1, len(props) + 1), index=order, name="rank_share")
    return share, rank.reindex(props.index)


def sector_summary(labels: gpd.GeoDataFrame, solar: np.ndarray, grid_share: np.ndarray,
                   households: np.ndarray, grid: Grid, drivers: pd.Series,
                   pop: np.ndarray | None = None) -> gpd.GeoDataFrame:
    labels = labels.to_crs(grid.crs).reset_index(drop=True)
    zones = area_zones(labels, grid)
    unserved = unserved_households(households, grid_share, solar)
    cols = {"solar_share": "census_solar_share", "grid_share": "census_grid_share",
            "unserved_share": "census_unserved_share"}
    keep = ["area_id", "sector", "district", *[c for c in cols if c in labels], "geometry"]
    out = labels[keep].rename(columns=cols)
    out["pred_solar_share"] = zone_means(zones, len(labels), solar, households)
    out["pred_grid_share"] = zone_means(zones, len(labels), grid_share, households)
    out["households"] = zone_sums(zones, len(labels), households)
    out["unserved_hh"] = zone_sums(zones, len(labels), unserved)
    if pop is not None:
        out["population"] = zone_sums(zones, len(labels), pop)
        out["area_km2"] = np.bincount(zones[zones >= 0], minlength=len(labels)) * pixel_km2(grid)
    out["top_drivers"] = out["area_id"].map(drivers).fillna("n/a")
    out["rank_unserved"] = out["unserved_hh"].rank(ascending=False, method="first").astype(int)
    return gpd.GeoDataFrame(out, geometry="geometry", crs=grid.crs)


def pixel_km2(grid: Grid) -> float:
    """Area of one grid square in km² at the grid's middle latitude."""
    _, lat = grid.centres()
    side = grid.res * KM_PER_DEG
    return float(side * side * math.cos(math.radians(float(lat.mean()))))


# ---------------------------------------------------------------- layers

def fmt(value: float, kind: str) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    if kind == "pct":
        return f"{100 * value:.0f}%" if abs(value) >= 0.01 or value == 0 else f"{100 * value:.1f}%"
    if kind == "int":
        return f"{value:,.0f}"
    if kind == "num1":
        return f"{value:,.1f}"
    return f"{value:,.2f}"


def colourise(values: np.ndarray, cmap: str, percentiles: tuple[float, float], log: bool
              ) -> tuple[str, list[str], list[dict]]:
    """PNG data URI of a raster coloured between two percentiles, its colour stops and ticks.

    Ticks are in the layer's own units (`log` layers are coloured on log1p but labelled in
    real values); the end ticks get "≤" / "≥" because values beyond them share the end colour.
    """
    from matplotlib import colormaps
    from PIL import Image

    scaled, lo, hi = normalise(values, percentiles, log=log)
    rgba = (colormaps[cmap](np.nan_to_num(scaled)) * 255).astype("uint8")
    rgba[..., 3] = np.where(np.isfinite(values), 255, 0)
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, "PNG", optimize=True)
    uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    stops = [_hex(colormaps[cmap](t)) for t in np.linspace(0, 1, 9)]
    ticks = []
    for t in (0.0, 0.5, 1.0):
        v = lo + t * (hi - lo)
        ticks.append({"t": t, "value": float(np.expm1(v) if log else v)})
    return uri, stops, ticks


def _hex(rgba) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(round(255 * c) for c in rgba[:3]))


def layer_values(stack: dict[str, np.ndarray], solar: np.ndarray, grid_share: np.ndarray,
                 households: np.ndarray, km2: float, min_population: float
                 ) -> dict[str, np.ndarray]:
    """The raster behind each layer, in the units its legend uses."""
    pop = stack["pop"]
    return {
        "underserved": unserved_households(households, grid_share, solar) / km2,
        "penetration": np.where(pop >= min_population, solar, np.nan),
        "ntl": np.clip(stack["ntl"], 0, None),
        "pop": pop / km2,
        "rwi": stack["rwi"],
        "dist_grid": stack["dist_grid"],
        "travel_min": stack["travel_min"],
        "built": stack["built"],
    }


# ---------------------------------------------------------------- page data

def _round_coords(obj, nd: int = 4):
    if isinstance(obj, (list, tuple)):
        return [_round_coords(o, nd) for o in obj]
    return round(obj, nd)


def _num(v, nd: int = 4):
    return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), nd)


def sector_features(summary: gpd.GeoDataFrame, train: pd.DataFrame) -> dict:
    """GeoJSON of the sectors with every number the details card shows."""
    feats = []
    simple = summary.geometry.simplify(0.001, preserve_topology=True)
    for r, geom in zip(summary.itertuples(), simple):
        t = train.loc[r.area_id] if r.area_id in train.index else {}
        area = getattr(r, "area_km2", np.nan)
        population = getattr(r, "population", np.nan)
        props = {
            "id": int(r.area_id), "sector": str(r.sector), "district": str(r.district),
            "rank": int(r.rank_unserved), "unserved_hh": _num(r.unserved_hh, 0),
            "households": _num(r.households, 0), "population": _num(population, 0),
            "area_km2": _num(area, 1),
            "density": _num(population / area if area and area > 0 else np.nan, 0),
            "census_solar": _num(getattr(r, "census_solar_share", np.nan)),
            "census_grid": _num(getattr(r, "census_grid_share", np.nan)),
            "census_unserved": _num(getattr(r, "census_unserved_share", np.nan)),
            "pred_solar": _num(r.pred_solar_share), "pred_grid": _num(r.pred_grid_share),
            "ntl": _num(t.get("ntl", np.nan), 3), "rwi": _num(t.get("rwi", np.nan), 3),
            "dist_grid": _num(t.get("dist_grid", np.nan), 2),
            "travel_min": _num(t.get("travel_min", np.nan), 0),
            "built": _num(t.get("built", np.nan)),
            "drivers": [] if r.top_drivers == "n/a" else str(r.top_drivers).split("; "),
        }
        pt = r.geometry.representative_point()
        props["pt"] = [round(pt.y, 4), round(pt.x, 4)]
        gj = geom.__geo_interface__
        feats.append({"type": "Feature", "properties": props,
                      "geometry": {"type": gj["type"], "coordinates": _round_coords(gj["coordinates"])}})
    return {"type": "FeatureCollection", "features": feats}


def layer_text(spec: dict) -> dict:
    return {k: spec[k] for k in LAYER_TEXT} | {"kind": spec.get("kind", "raster")}


def sector_layer(spec: dict) -> dict:
    """A layer drawn by colouring sectors: its ramp in the menu is one band per route."""
    n = len(ROUTES)
    stops = [f"{r['colour']} {100 * i / n:.0f}% {100 * (i + 1) / n:.0f}%"
             for i, r in enumerate(ROUTES)]
    return layer_text(spec) | {"image": None, "stops": stops, "ticks": []}


def page_data(cfg: dict, summary: gpd.GeoDataFrame, train: pd.DataFrame,
              values: dict[str, np.ndarray], bounds, cal: dict) -> dict:
    pct = tuple(cfg["export"]["normalise_percentiles"])
    layers = []
    for spec in LAYERS:
        if spec.get("kind") == "sectors":
            layers.append(sector_layer(spec))
            continue
        uri, stops, ticks = colourise(values[spec["key"]], spec["cmap"], pct, spec["log"])
        for i, tick in enumerate(ticks):
            label = fmt(tick["value"], spec["format"])
            # Values beyond the end ticks share the end colours.
            prefix = "≥ " if i == 2 else "≤ " if i == 0 and tick["value"] != 0 else ""
            tick["label"] = prefix + label
        layers.append(layer_text(spec) | {"image": uri, "stops": stops, "ticks": ticks})

    sectors = sector_features(summary, train)
    props = pd.DataFrame([f["properties"] for f in sectors["features"]])
    medians = {k: _num(props[k].median()) for k in
               ("unserved_hh", "pred_solar", "ntl", "density", "rwi", "dist_grid", "travel_min",
                "built")}
    top = props.sort_values("rank").head(TOP_N)["id"].tolist()
    country = cfg["country"]
    data = {
        "title": f"Underserved Solar Markets · {country['name']}",
        "country": country["name"], "year": cfg["reference_year"],
        "bounds": [[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
        "basemaps": BASEMAPS, "default_basemap": "grey", "default_layer": LAYERS[0]["key"],
        "layers": layers, "sectors": sectors, "medians": medians, "top": top,
        "n_sectors": len(props),
        "totals": {"unserved_hh": _num(props["unserved_hh"].sum(), 0),
                   "households": _num(props["households"].sum(), 0)},
        "calibration": {"target_share": cal.get("target_share"),
                        "source": cal.get("target_source")},
        "links": LINKS,
    }
    return add_user_fields(data, cfg)


def confidence_notes(props: pd.DataFrame, district_errors: pd.Series, rules: dict
                     ) -> list[list[str]]:
    """Plain-language reasons to check each sector on the ground before acting on it.

    A sector gets a note when the census and the model disagree on its solar share by more than
    `disagree_pp` points, or when the model is off by `district_error_pp` points or more in its
    district (`district_errors`: model minus census, in points, by district name). No notes means
    the usual accuracy.
    """
    out = []
    for r in props.itertuples():
        notes = []
        census, model = r.census_solar, r.pred_solar
        if pd.notna(census) and pd.notna(model) and 100 * abs(model - census) > rules["disagree_pp"]:
            notes.append(f"The census says {census:.0%} of homes here use solar; the model says "
                         f"{model:.0%}.")
        err = district_errors.get(r.district)
        if err is not None and abs(err) >= rules["district_error_pp"]:
            way = "under" if err < 0 else "over"
            notes.append(f"In {r.district} district the model {way}-estimates solar use by "
                         f"{abs(err):.0f} percentage points on average.")
        out.append(notes)
    return out


def model_errors(reports: Path) -> dict[str, float]:
    """Each target's average model error in percentage points, in districts the model has not
    seen (blocked cross-validation); the page shows every model share as value ± this error."""
    path = reports / "cv_results.csv"
    if not path.exists():
        return {}
    cv = pd.read_csv(path)
    blocked = cv[cv["cv"].str.startswith("blocked") & (cv["model"] == "lightgbm")]
    return {t: round(float(e), 1) for t, e in zip(blocked["target"], blocked["mae_pp"])}


def survey_since(reports: Path) -> dict | None:
    """National shares from the latest household survey, to show how far things moved since 2022."""
    path = reports / "dhs_validation.json"
    if not path.exists():
        return None
    dhs = json.loads(path.read_text(encoding="utf-8"))
    return {"survey": dhs["survey"], "solar": _num(dhs["national"]["solar"]),
            "grid": _num(dhs["national"]["grid"]), "none": _num(dhs["national"]["none"])}


def layer_downloads(outputs: Path) -> list[dict]:
    """The EAE layers in outputs/ (each GeoTIFF with its .yml metadata) as links on GitHub main."""
    out = []
    for meta in sorted(outputs.glob("*.yml")):
        info = yaml.safe_load(meta.read_text(encoding="utf-8"))
        tif = outputs / info["file"]
        if tif.exists():
            out.append({"name": info["name"], "file": tif.name, "bytes": tif.stat().st_size,
                        "url": f"{REPO}/raw/main/outputs/{tif.name}",
                        "meta_url": f"{REPO}/blob/main/outputs/{meta.name}"})
    return out


# Sector fields add_user_fields() derives; the full run also writes them to the ranked list.
DERIVED = ("route", "unserved_share", "rank_share", "checks")


def add_user_fields(data: dict, cfg: dict) -> dict:
    """What the page derives from the sector numbers: each sector's delivery route, its share of
    homes without light and rank by that share, reasons to check it on the ground first, and the
    route totals; plus the layer downloads, the model's errors, the latest survey's national shares
    and where field corrections go.

    Both the full run and --from-map call it, so both build the same page; running it again
    gives the same result.
    """
    feats = data["sectors"]["features"]
    props = pd.DataFrame([f["properties"] for f in feats])
    rules = cfg["webmap"]["routes"]
    national = data["calibration"]["target_share"]
    props["route"] = delivery_routes(props, national, rules)
    props["unserved_share"], props["rank_share"] = share_ranks(props)
    paths = get_paths(cfg)
    errors = paths.reports / "calibration_districts.csv"
    errors = (pd.read_csv(errors).set_index("district")["error_pp"] if errors.exists()
              else pd.Series(dtype=float))
    checks = confidence_notes(props, errors, cfg["webmap"]["confidence"])
    for f, route, share, rank, notes in zip(feats, props["route"], props["unserved_share"],
                                            props["rank_share"], checks):
        f["properties"] |= {"route": route, "unserved_share": _num(share), "rank_share": int(rank),
                            "checks": notes}
    data["routes"] = [r | {"sectors": int((props["route"] == r["key"]).sum()),
                           "unserved_hh": _num(props.loc[props["route"] == r["key"],
                                                         "unserved_hh"].sum(), 0)}
                      for r in ROUTES]
    data["route_rules"] = {"grid_share_min": rules["grid_share_min"],
                           "grid_km_max": rules["grid_km_max"],
                           "solar_share_min": _num(rules.get("solar_share_min") or national)}
    data["downloads"] = layer_downloads(paths.outputs)
    data["since"] = survey_since(paths.reports)
    data["errors_pp"] = model_errors(paths.reports)   # not shown yet: accuracy is left out of the demo
    data["confidence"] = dict(cfg["webmap"]["confidence"])
    data["feedback_url"] = cfg["webmap"].get("feedback_url")
    return data


def render_html(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/").replace("<!--", "<\\u0021--")   # valid JSON, safe in <script>
    page = TEMPLATE.read_text(encoding="utf-8")
    return page.replace("__TITLE__", escape(data["title"])).replace("__MAP_DATA__", payload)


def read_map_data(html: str) -> dict:
    """The page data embedded in a built map.html (the inverse of render_html)."""
    m = re.search(r'<script id="map-data" type="application/json">(.*?)</script>', html, re.DOTALL)
    if not m:
        raise ValueError("no map data block in this page; was it built by solar_markets.webmap?")
    return json.loads(m.group(1))


def rebuild_from_map(html: str, cfg: dict) -> dict:
    """Page data of a built map.html, with the layer wording and derived fields refreshed.

    Each raster layer keeps the image, colours and ticks it was built with, and add_user_fields
    works from the sector numbers already in the page, so this needs no data.
    """
    data = read_map_data(html)
    built = {layer["key"]: layer for layer in data["layers"]}
    rasters = [spec for spec in LAYERS if spec.get("kind") != "sectors"]
    missing = [spec["key"] for spec in rasters if spec["key"] not in built]
    if missing:
        raise ValueError(f"layers {missing} are not in this map yet; run the full webmap stage")
    data["layers"] = [sector_layer(spec) if spec.get("kind") == "sectors" else
                      layer_text(spec) | {k: built[spec["key"]][k] for k in LAYER_RASTER}
                      for spec in LAYERS]
    data["links"] = LINKS
    return add_user_fields(data, cfg)


def write_page(out: Path, data: dict) -> None:
    out.write_text(render_html(data), encoding="utf-8")
    print(f"Wrote {out} ({out.stat().st_size / 1e6:.1f} MB, {len(data['layers'])} layers, "
          f"{data['n_sectors']} sectors)")


# ---------------------------------------------------------------- pipeline stage

def run(cfg: dict) -> None:
    paths = get_paths(cfg)
    features = list(cfg["features"])
    cal = json.loads((paths.reports / "calibration.json").read_text())

    def read(path):
        with rasterio.open(path) as src:
            a = src.read(1, masked=True).astype("float32")
            return a.filled(np.nan), src.bounds

    with rasterio.open(paths.processed / "feature_stack.tif") as src:
        stack = dict(zip(src.descriptions, src.read()))
        grid = Grid(src.transform, src.width, src.height, str(src.crs))
    solar, bounds = read(paths.outputs / "solar_share_calibrated.tif")
    grid_share, _ = read(paths.outputs / "grid_share_pred.tif")
    households = stack["pop"] / cal["avg_household_size"]

    shap = pd.read_csv(paths.reports / "shap_values.csv")
    shap = shap[shap["target"] == cfg["model"]["targets"][0]]
    train = pd.read_csv(paths.processed / "train_table.csv").set_index("area_id")
    drivers = top_drivers(shap, train, features)

    summary = sector_summary(gpd.read_file(paths.processed / "labels.gpkg"), solar, grid_share,
                             households, grid, drivers, pop=stack["pop"])
    values = layer_values(stack, solar, grid_share, households, pixel_km2(grid),
                          cfg["export"]["min_population"])
    data = page_data(cfg, summary, train, values, bounds, cal)
    derived = pd.DataFrame([f["properties"] for f in data["sectors"]["features"]]).set_index("id")
    for col in DERIVED:
        summary[col] = summary["area_id"].map(derived[col])
    summary["checks"] = summary["checks"].map(" ".join)

    summary.to_file(paths.processed / "sector_summary.gpkg", driver="GPKG")
    ranked = summary.sort_values("rank_unserved").drop(columns="geometry")
    ranked.to_csv(paths.reports / "top_underserved_sectors.csv", index=False)
    write_page(paths.docs / "map.html", data)
    print("Top underserved sectors:")
    print(ranked.head(TOP_N)[["rank_unserved", "sector", "district", "unserved_hh", "route",
                              "top_drivers"]].to_string(index=False))


def rebuild(cfg: dict) -> None:
    """Re-render docs/map.html around the data the last full run embedded in it."""
    out = get_paths(cfg).docs / "map.html"
    write_page(out, rebuild_from_map(out.read_text(encoding="utf-8"), cfg))


def main() -> None:
    args = cli_args(__doc__.splitlines()[0],
                    {"--from-map": "rebuild docs/map.html from the data already in it "
                                   "(after a template or wording change; needs no data/processed)"})
    cfg = load_config(args.config)
    get_paths(cfg).ensure()
    if args.from_map:
        rebuild(cfg)
    else:
        run(cfg)


if __name__ == "__main__":
    main()
