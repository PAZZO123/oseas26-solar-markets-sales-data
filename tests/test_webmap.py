import copy
import json

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from solar_markets import calibrate as C
from solar_markets import export as E
from solar_markets import features as F
from solar_markets import model as M
from solar_markets import webmap as W
from solar_markets.config import DEFAULT_CONFIG, load_config

CFG = load_config(DEFAULT_CONFIG)
FEATURES = CFG["features"]


def test_top_drivers_text():
    shap = pd.DataFrame({"area_id": [1, 2], "ntl": [-0.05, 0.0], "rwi": [0.01, 0.02],
                         "dist_grid": [0.03, -0.001]})
    values = pd.DataFrame({"ntl": [0.1, 5.0], "rwi": [-1.0, 1.0], "dist_grid": [9.0, 1.0]},
                          index=[1, 2])
    out = W.top_drivers(shap, values, ["ntl", "rwi", "dist_grid"], n=2)
    assert out[1] == "low night lights (-5.0 pp); high distance to the grid (+3.0 pp)"
    assert out[2].startswith("high wealth (RWI) (+2.0 pp)")


def test_zone_sums_ignore_nan_and_unzoned():
    zones = np.array([0, 0, 1, -1])
    assert W.zone_sums(zones, 3, np.array([1.0, np.nan, 2.0, 5.0])).tolist() == [1.0, 2.0, 0.0]


def test_pipeline_from_features_to_map(tmp_path):
    """Synthetic feature stack -> model -> calibrate -> export -> web map."""
    cfg = copy.deepcopy(CFG)
    cfg["country"]["bbox"] = [30.0, -2.0, 30.2, -1.8]
    cfg["paths"] = {k: str(tmp_path / k) for k in cfg["paths"]}
    for k in cfg["paths"]:
        (tmp_path / k).mkdir()
    cfg["model"]["lightgbm"] = cfg["model"]["lightgbm"] | {"min_child_samples": 3,
                                                           "n_estimators": 50}
    processed, reports = tmp_path / "processed", tmp_path / "reports"
    grid = F.make_grid(cfg)
    rng = np.random.default_rng(3)

    bands = {n: rng.uniform(0, 5, size=grid.shape).astype("float32") for n in FEATURES}
    bands["pop"] = rng.uniform(10, 2000, size=grid.shape).astype("float32")
    for b in bands.values():
        b[:, -1] = np.nan
    F.write_stack(bands, FEATURES, grid, processed / "feature_stack.tif")

    res = grid.res
    rows = []
    for i in range(6):
        for j in range(6):
            x0, y1 = grid.transform.c + 4 * j * res, grid.transform.f - 4 * i * res
            rows.append({"area_id": 100 + 6 * i + j, "sector": f"Sector {6 * i + j}",
                         "district_code": i, "district": f"District {i}",
                         "geometry": box(x0, y1 - 4 * res, x0 + 4 * res, y1)})
    labels = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    table = F.training_table(labels, bands, FEATURES, grid)
    labels["solar_share"] = np.clip(0.05 + table["dist_grid"] / 20, 0, 1)
    labels["grid_share"] = np.clip(1 - table["dist_grid"] / 5, 0, 1) * 0.7
    table[["solar_share", "grid_share"]] = labels[["solar_share", "grid_share"]]
    table.to_csv(processed / "train_table.csv", index=False)
    labels.to_file(processed / "labels.gpkg", layer="sectors", driver="GPKG")
    labels.groupby(["district_code", "district"], as_index=False)["solar_share"].mean().to_csv(
        processed / "labels_district.csv", index=False)
    (reports / "labels_summary.json").write_text(
        json.dumps({"solar_share": 0.156, "avg_household_size": 4.0}))

    M.run(cfg)
    C.run(cfg)
    E.run(cfg)
    W.run(cfg)

    summary = gpd.read_file(processed / "sector_summary.gpkg")
    assert len(summary) == 36
    assert sorted(summary["rank_unserved"]) == list(range(1, 37))
    assert summary["pred_solar_share"].between(0, 1).all()
    assert (summary["unserved_hh"] >= 0).all()
    assert summary["top_drivers"].str.contains(r"\(\S+ pp\)").all()
    assert summary["households"].sum() == pytest.approx(np.nansum(bands["pop"]) / 4.0, rel=1e-4)

    ranked = pd.read_csv(reports / "top_underserved_sectors.csv")
    assert ranked["unserved_hh"].is_monotonic_decreasing
    assert set(ranked["route"]) <= {r["key"] for r in W.ROUTES}

    html = (tmp_path / "docs" / "map.html").read_text(encoding="utf-8")
    assert "__MAP_DATA__" not in html and "__TITLE__" not in html
    data = map_data(html)

    # One entry per layer; raster layers have an image, a colour ramp and ticks in their own units.
    assert [layer["key"] for layer in data["layers"]] == [s["key"] for s in W.LAYERS]
    for layer in data["layers"]:
        if layer["kind"] == "sectors":
            assert layer["image"] is None and len(layer["stops"]) == len(W.ROUTES)
            continue
        assert layer["image"].startswith("data:image/png;base64,")
        assert len(layer["stops"]) == 9 and len(layer["ticks"]) == 3
        values = [t["value"] for t in layer["ticks"]]
        assert values == sorted(values) and all(t["label"] for t in layer["ticks"])

    # Every sector carries the numbers the details card shows for every layer.
    feats = data["sectors"]["features"]
    assert len(feats) == 36 and data["n_sectors"] == 36
    for f in feats:
        p = f["properties"]
        for key in [s["metric"] for s in W.LAYERS] + ["rank", "sector", "district", "pt", "drivers",
                                                      "route"]:
            assert key in p, key
    assert sorted(f["properties"]["rank"] for f in feats) == list(range(1, 37))
    ranks = {f["properties"]["id"]: f["properties"]["rank"] for f in feats}
    assert [ranks[i] for i in data["top"]] == list(range(1, 11))
    assert data["medians"]["unserved_hh"] is not None

    # Every sector has one delivery route, and the route totals add up to the whole country.
    assert [r["key"] for r in data["routes"]] == [r["key"] for r in W.ROUTES]
    assert sum(r["sectors"] for r in data["routes"]) == 36
    assert sum(r["unserved_hh"] for r in data["routes"]) == pytest.approx(
        sum(f["properties"]["unserved_hh"] for f in feats), abs=36)

    # Starts on the underserved layer and on a basemap that also works from a local file.
    assert data["default_layer"] == "underserved"
    assert "arcgisonline" in data["basemaps"][data["default_basemap"]]["url"]
    assert "tile.openstreetmap.org" not in html


def map_data(html: str) -> dict:
    return W.read_map_data(html)


def sector_props(**over) -> dict:
    p = {"id": 1, "census_grid": 0.2, "census_solar": 0.05, "pred_grid": 0.3, "pred_solar": 0.1,
         "dist_grid": 3.0, "unserved_hh": 1000.0}
    return p | over


def built_map(layers: list[dict]) -> str:
    """A map.html as an earlier run (without the derived fields) would have written it."""
    feats = [{"type": "Feature", "properties": sector_props(id=i), "geometry": None}
             for i in (1, 2)]
    return W.render_html({"title": "T", "layers": layers, "n_sectors": 2, "links": {},
                          "calibration": {"target_share": 0.14},
                          "sectors": {"type": "FeatureCollection", "features": feats}})


RULES = {"grid_share_min": 0.5, "grid_km_max": 1.0, "solar_share_min": None}


def test_delivery_routes():
    props = pd.DataFrame([
        sector_props(census_grid=0.6),                      # most homes on the grid
        sector_props(dist_grid=0.5),                        # few on the grid, but lines are close
        sector_props(census_solar=0.3),                     # solar above the national share
        sector_props(census_solar=0.14),                    # exactly the national share
        sector_props(),                                     # little grid, little solar, far away
        sector_props(census_grid=None, census_solar=None, pred_grid=0.7),   # model fills in
    ])
    routes = W.delivery_routes(props, 0.14, RULES)
    assert routes.tolist() == ["grid", "grid", "solar_grow", "solar_grow", "solar_gap", "grid"]
    # A configured solar threshold replaces the national share.
    assert W.delivery_routes(props, 0.14, RULES | {"solar_share_min": 0.35})[2] == "solar_gap"


def test_rebuild_from_map_keeps_rasters_and_refreshes_wording():
    layers = [{k: spec[k] for k in W.LAYER_TEXT}
              | {"name": "old wording", "image": "data:image/png;base64," + spec["key"],
                 "stops": ["#000000"] * 9, "ticks": [{"t": 0.0, "value": 0.0, "label": "0"}]}
              for spec in W.LAYERS if spec.get("kind") != "sectors"]

    data = W.rebuild_from_map(built_map(layers), CFG)
    assert [layer["name"] for layer in data["layers"]] == [s["name"] for s in W.LAYERS]
    rasters = [layer["image"] for layer in data["layers"] if layer["kind"] == "raster"]
    assert rasters == [layer["image"] for layer in layers]
    assert [f["properties"]["route"] for f in data["sectors"]["features"]] == ["solar_gap"] * 2
    assert data["links"] == W.LINKS
    # Rebuilding the rebuilt page changes nothing.
    assert W.rebuild_from_map(W.render_html(data), CFG) == data


def test_rebuild_from_map_needs_every_raster_layer():
    with pytest.raises(ValueError, match="full webmap stage"):
        W.rebuild_from_map(built_map([]), CFG)
    with pytest.raises(ValueError, match="no map data"):
        W.read_map_data("<html></html>")


def test_render_html_keeps_data_inside_its_script_block():
    data = {"title": "T <b>", "evil": "</script><script>alert(1)</script><!--"}
    html = W.render_html(data)
    assert "</script><script>alert(1)" not in html
    assert "<title>T &lt;b&gt;</title>" in html
    assert map_data(html)["evil"] == data["evil"]


def test_fmt():
    assert W.fmt(0.1234, "pct") == "12%"
    assert W.fmt(0.004, "pct") == "0.4%"
    assert W.fmt(12345.6, "int") == "12,346"
    assert W.fmt(2.345, "num1") == "2.3"
    assert W.fmt(float("nan"), "num2") == "n/a"


def test_colourise_ticks_are_in_real_units_for_log_layers():
    values = np.array([[0.0, 1.0, 10.0], [100.0, 1000.0, np.nan]], dtype="float32")
    uri, stops, ticks = W.colourise(values, "viridis", (0, 100), log=True)
    assert uri.startswith("data:image/png;base64,") and len(stops) == 9
    assert ticks[0]["value"] == pytest.approx(0.0, abs=1e-6)
    assert ticks[-1]["value"] == pytest.approx(1000.0, rel=1e-4)
    assert 10 < ticks[1]["value"] < 100      # midpoint on the log scale, not 500
