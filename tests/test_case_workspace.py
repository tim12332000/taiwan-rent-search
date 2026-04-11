from pathlib import Path

from src.case_workspace import (
    build_case_current_dataset_path,
    build_case_dir,
    build_case_search_app_path,
    ensure_case_workspace,
    sync_case_current_dataset,
)


def test_ensure_case_workspace_writes_metadata(tmp_path):
    case_dir = ensure_case_workspace(
        "songren_100",
        destination_address="台北市信義區松仁路100號",
        county="台北市",
        district="信義區",
        base_dir=tmp_path,
    )

    assert case_dir == tmp_path / "songren_100"
    metadata = (case_dir / "case.json").read_text(encoding="utf-8")
    assert "台北市信義區松仁路100號" in metadata
    assert "current_dataset.csv" in metadata
    assert "search_app.html" in metadata


def test_sync_case_current_dataset_copies_snapshot(tmp_path):
    snapshot = tmp_path / "snapshot.csv"
    snapshot.write_text("id\n1\n", encoding="utf-8")

    current_path = sync_case_current_dataset(snapshot, case_slug="songren_100", base_dir=tmp_path)

    assert current_path == build_case_current_dataset_path("songren_100", tmp_path)
    assert current_path.read_text(encoding="utf-8") == "id\n1\n"
