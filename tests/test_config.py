import sys

from solar_markets.config import DEFAULT_CONFIG, cli_args, get_paths, load_config


def test_config_loads():
    cfg = load_config(DEFAULT_CONFIG)
    assert cfg["country"]["iso3"] == "RWA"
    assert cfg["grid"]["resolution_m"] > 0
    target = cfg["calibration"]["target_share"]
    assert target is None or 0 < target < 1


def test_features_are_unique_and_log_features_known():
    cfg = load_config(DEFAULT_CONFIG)
    feats = cfg["features"]
    assert len(feats) == len(set(feats))
    assert set(cfg["log_features"]) <= set(feats)


def test_label_code_groups_do_not_overlap():
    census = load_config(DEFAULT_CONFIG)["labels"]["census"]
    groups = [set(census[k]) for k in ("solar_codes", "grid_codes", "unserved_codes")]
    assert not (groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2])


def test_paths_resolve_inside_project(tmp_path):
    cfg = load_config(DEFAULT_CONFIG)
    paths = get_paths(cfg, root=tmp_path)
    paths.ensure()
    assert paths.raw.is_dir() and paths.outputs.is_dir()
    assert paths.raw.is_relative_to(tmp_path)


def test_cli_args_adds_on_off_flags(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["stage", "--from-map"])
    args = cli_args("stage", {"--from-map": "rebuild"})
    assert args.from_map is True and args.config == str(DEFAULT_CONFIG)
    monkeypatch.setattr(sys, "argv", ["stage"])
    assert cli_args("stage", {"--from-map": "rebuild"}).from_map is False
