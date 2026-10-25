"""Load `config.yml` and resolve project paths."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config.yml"


@dataclass(frozen=True)
class Paths:
    raw: Path
    interim: Path
    processed: Path
    outputs: Path
    reports: Path
    models: Path
    docs: Path

    def ensure(self) -> None:
        for p in (self.raw, self.interim, self.processed, self.outputs, self.reports, self.models,
                  self.docs):
            p.mkdir(parents=True, exist_ok=True)


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for key in ("country", "grid", "labels", "features", "model", "calibration", "paths"):
        if key not in cfg:
            raise KeyError(f"'{key}' missing from {path}")
    return cfg


def get_paths(cfg: dict[str, Any], root: Path = PROJECT_ROOT) -> Paths:
    p = cfg["paths"]
    return Paths(**{name: (root / p[name]).resolve() for name in Paths.__dataclass_fields__})


def use_system_certificates() -> None:
    """Verify HTTPS against the operating system's certificate store instead of certifi's list.

    Antivirus HTTPS scanning (e.g. Avast) and company proxies re-sign traffic with a root
    certificate that is only in the Windows store, so Earth Engine calls fail with
    CERTIFICATE_VERIFY_FAILED otherwise.
    """
    import truststore

    truststore.inject_into_ssl()


def cli_args(description: str, flags: dict[str, str] | None = None) -> argparse.Namespace:
    """Common command-line arguments for every pipeline stage, plus on/off `flags` {flag: help}."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="path to config.yml")
    for flag, help_text in (flags or {}).items():
        parser.add_argument(flag, action="store_true", help=help_text)
    return parser.parse_args()
