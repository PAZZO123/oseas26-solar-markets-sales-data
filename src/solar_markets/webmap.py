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
# with; `format` says how to print it (see fmt()).
LAYERS = [
    {"key": "underserved", "group": "Results", "name": "Underserved market",
     "short": "Households with neither grid nor solar",
     "description": "Estimated households per km² that light their homes with neither grid "
                    "electricity nor solar. Darker = more families without light. This is the "
                    "layer funders act on.",
     "cmap": "magma_r", "log": False, "unit": "households per km²", "format": "int",
     "metric": "unserved_hh", "metric_label": "households with neither grid nor solar",
     "higher_is": "more households without light"},
    {"key": "penetration", "group": "Results", "name": "Solar penetration",
     "short": "Share of homes lit by solar",
     "description": "Estimated share of households whose main light is solar (calibrated to the "
                    "2022 census). Blank where almost nobody lives.",
     "cmap": "viridis", "log": False, "unit": "of households", "format": "pct",
     "metric": "pred_solar", "metric_label": "of households use solar (model estimate)",
     "higher_is": "more solar"},
    {"key": "ntl", "group": "Clues the model uses", "name": "Night lights",
     "short": "Brightness at night (VIIRS 2022)",
     "description": "Average night-time brightness seen by satellite. Bright = grid electricity "
                    "and towns. Solar lamps are too dim to show, which is why the model needs "
                    "other clues.",
     "cmap": "inferno", "log": True, "unit": "nW/cm²/sr", "format": "num2",
     "metric": "ntl", "metric_label": "night-light brightness where people live",
     "higher_is": "brighter"},
    {"key": "pop", "group": "Clues the model uses", "name": "Population",
     "short": "People per km² (WorldPop 2020)",
     "description": "How many people live in each square kilometre. More people means more "
                    "potential customers and more need.",
     "cmap": "YlGnBu", "log": True, "unit": "people per km²", "format": "int",
     "metric": "density", "metric_label": "people per km² on average",
     "higher_is": "more people"},
    {"key": "rwi", "group": "Clues the model uses", "name": "Wealth",
     "short": "Relative Wealth Index (Meta)",
     "description": "Estimated wealth compared with the rest of Rwanda, from about -1 (poorer) "
                    "to +2 (richer). Wealthier areas can afford solar more easily.",
     "cmap": "PuOr", "log": False, "unit": "index", "format": "num2",
     "metric": "rwi", "metric_label": "wealth index where people live",
     "higher_is": "wealthier"},
    {"key": "dist_grid", "group": "Clues the model uses", "name": "Distance to the grid",
     "short": "Km to the nearest power line (Gridfinder)",
     "description": "Distance to the nearest likely power line. Close to the grid, families "
                    "usually connect to it; far away, solar or nothing.",
     "cmap": "YlOrBr", "log": False, "unit": "km", "format": "num1",
     "metric": "dist_grid", "metric_label": "km to the grid where people live",
     "higher_is": "farther from the grid"},
    {"key": "travel_min", "group": "Clues the model uses", "name": "Travel time to a city",
     "short": "Minutes to the nearest city (2015)",
     "description": "Travel time to the nearest city of 50,000 or more people. Remote places "
                    "are harder for solar sales agents to reach.",
     "cmap": "BuPu", "log": False, "unit": "minutes", "format": "int",
     "metric": "travel_min", "metric_label": "minutes to a city where people live",
     "higher_is": "more remote"},
    {"key": "built", "group": "Clues the model uses", "name": "Built-up area",
     "short": "Share of land with buildings (ESA 2021)",
     "description": "Share of each square covered by buildings. High in towns, very low in "
                    "scattered rural settlements.",
     "cmap": "OrRd", "log": False, "unit": "of land", "format": "pct",
     "metric": "built", "metric_label": "of land built up where people live",
     "higher_is": "more built-up"},
]
# The fields of a LAYERS entry the page uses; the rest of a page layer is its raster and legend.
LAYER_TEXT = ("key", "group", "name", "short", "description", "unit", "format", "metric",
              "metric_label", "higher_is")
LAYER_RASTER = ("image", "stops", "ticks")


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


def page_data(cfg: dict, summary: gpd.GeoDataFrame, train: pd.DataFrame,
              values: dict[str, np.ndarray], bounds, cal: dict) -> dict:
    pct = tuple(cfg["export"]["normalise_percentiles"])
    layers = []
    for spec in LAYERS:
        uri, stops, ticks = colourise(values[spec["key"]], spec["cmap"], pct, spec["log"])
        for i, tick in enumerate(ticks):
            label = fmt(tick["value"], spec["format"])
            # Values beyond the end ticks share the end colours.
            prefix = "≥ " if i == 2 else "≤ " if i == 0 and tick["value"] != 0 else ""
            tick["label"] = prefix + label
        layers.append({k: spec[k] for k in LAYER_TEXT}
                      | {"image": uri, "stops": stops, "ticks": ticks})

    sectors = sector_features(summary, train)
    props = pd.DataFrame([f["properties"] for f in sectors["features"]])
    medians = {k: _num(props[k].median()) for k in
               ("unserved_hh", "pred_solar", "ntl", "density", "rwi", "dist_grid", "travel_min",
                "built")}
    top = props.sort_values("rank").head(TOP_N)["id"].tolist()
    country = cfg["country"]
    return {
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
        "links": {"repo": "https://github.com/PAZZO123/oseas26-solar-markets-sales-data",
                  "limitations": "https://github.com/PAZZO123/oseas26-solar-markets-sales-data/blob/main/LIMITATIONS.md"},
    }


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


def rebuild_from_map(html: str) -> dict:
    """Page data of a built map.html, with the layer wording refreshed from LAYERS.

    Each layer keeps the raster, colours and ticks it was built with, so this needs no data.
    """
    data = read_map_data(html)
    built = {layer["key"]: layer for layer in data["layers"]}
    missing = [spec["key"] for spec in LAYERS if spec["key"] not in built]
    if missing:
        raise ValueError(f"layers {missing} are not in this map yet; run the full webmap stage")
    data["layers"] = [{k: spec[k] for k in LAYER_TEXT}
                      | {k: built[spec["key"]][k] for k in LAYER_RASTER} for spec in LAYERS]
    return data


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
    summary.to_file(paths.processed / "sector_summary.gpkg", driver="GPKG")
    ranked = summary.sort_values("rank_unserved").drop(columns="geometry")
    ranked.to_csv(paths.reports / "top_underserved_sectors.csv", index=False)

    values = layer_values(stack, solar, grid_share, households, pixel_km2(grid),
                          cfg["export"]["min_population"])
    data = page_data(cfg, summary, train, values, bounds, cal)
    write_page(paths.docs / "map.html", data)
    print("Top underserved sectors:")
    print(ranked.head(TOP_N)[["rank_unserved", "sector", "district", "unserved_hh",
                              "top_drivers"]].to_string(index=False))


def rebuild(cfg: dict) -> None:
    """Re-render docs/map.html around the data the last full run embedded in it."""
    out = get_paths(cfg).docs / "map.html"
    write_page(out, rebuild_from_map(out.read_text(encoding="utf-8")))


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
