"""Helpers for repeatable destination-specific workspaces."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path


DEFAULT_CASES_DIR = Path("data") / "cases"


def build_case_dir(case_slug: str, base_dir: str | Path = DEFAULT_CASES_DIR) -> Path:
    return Path(base_dir) / case_slug


def build_case_metadata_path(case_slug: str, base_dir: str | Path = DEFAULT_CASES_DIR) -> Path:
    return build_case_dir(case_slug, base_dir) / "case.json"


def build_case_snapshot_dataset_path(case_slug: str, base_dir: str | Path = DEFAULT_CASES_DIR) -> Path:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    return build_case_dir(case_slug, base_dir) / f"dataset_{timestamp}.csv"


def build_case_current_dataset_path(case_slug: str, base_dir: str | Path = DEFAULT_CASES_DIR) -> Path:
    return build_case_dir(case_slug, base_dir) / "current_dataset.csv"


def build_case_search_app_path(case_slug: str, base_dir: str | Path = DEFAULT_CASES_DIR) -> Path:
    return build_case_dir(case_slug, base_dir) / "search_app.html"


def ensure_case_workspace(
    case_slug: str,
    *,
    destination_address: str,
    county: str = "",
    district: str = "",
    base_dir: str | Path = DEFAULT_CASES_DIR,
) -> Path:
    case_dir = build_case_dir(case_slug, base_dir)
    case_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "slug": case_slug,
        "destination_address": destination_address,
        "county": county,
        "district": district,
        "current_dataset": build_case_current_dataset_path(case_slug, base_dir).name,
        "search_app": build_case_search_app_path(case_slug, base_dir).name,
    }
    build_case_metadata_path(case_slug, base_dir).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return case_dir


def sync_case_current_dataset(
    dataset_path: str | Path,
    *,
    case_slug: str,
    base_dir: str | Path = DEFAULT_CASES_DIR,
) -> Path:
    current_path = build_case_current_dataset_path(case_slug, base_dir)
    current_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dataset_path, current_path)
    return current_path
