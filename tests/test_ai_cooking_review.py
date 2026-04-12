import json
from pathlib import Path

import requests

from src.ai_cooking_review import (
    ai_cooking_label_to_score,
    ai_review_candidate_priority,
    build_codex_exec_command,
    build_subprocess_run_kwargs,
    build_dataset_ai_reviews_path,
    build_dataset_ai_usage_log_path,
    download_listing_images,
    image_urls_hash,
    load_ai_reviews,
    resolve_codex_command,
    resolve_dataset_path,
    save_ai_reviews,
)


def test_ai_cooking_label_to_score_maps_labels():
    assert ai_cooking_label_to_score("適合煮飯") == 3
    assert ai_cooking_label_to_score("可勉強煮") == 2
    assert ai_cooking_label_to_score("不確定") == 1
    assert ai_cooking_label_to_score("不適合煮飯") == 0


def test_image_urls_hash_is_stable():
    urls = ["https://img/1.jpg", "https://img/2.jpg"]
    assert image_urls_hash(urls) == image_urls_hash(urls)


def test_save_and_load_ai_reviews_round_trip(tmp_path):
    path = tmp_path / "reviews.json"
    payload = {
        "591-1": {
            "label": "適合煮飯",
            "score": 3,
            "confidence": 0.92,
            "reason": "文字同時提到流理臺與可煮飯設備",
            "image_urls_hash": "abc123",
        }
    }

    save_ai_reviews(path, payload)

    assert load_ai_reviews(path) == payload


def test_build_dataset_ai_paths_use_dataset_directory():
    dataset_path = Path("data/cases/songren_100/current_dataset.csv")

    assert build_dataset_ai_reviews_path(dataset_path).as_posix().endswith("data/cases/songren_100/ai_cooking_reviews.json")
    assert build_dataset_ai_usage_log_path(dataset_path).as_posix().endswith("data/cases/songren_100/ai_usage.jsonl")


def test_ai_review_candidate_priority_prefers_ambiguous_items():
    ambiguous = {"description": "近捷運", "images": "https://img/1.jpg"}
    no_signal = {"description": "生活機能佳", "images": ""}
    explicit = {"description": "可開伙 有流理台", "images": "https://img/1.jpg"}

    assert ai_review_candidate_priority(ambiguous)[0] == 0
    assert ai_review_candidate_priority(no_signal)[0] == 1
    assert ai_review_candidate_priority(explicit)[0] == 2


def test_resolve_dataset_path_prefers_explicit_input(tmp_path):
    dataset_path = tmp_path / "sample.csv"

    assert resolve_dataset_path(str(dataset_path), use_latest=False) == dataset_path


def test_resolve_dataset_path_uses_latest_when_requested(monkeypatch, tmp_path):
    latest = tmp_path / "latest.csv"
    monkeypatch.setattr("src.ai_cooking_review.latest_dataset_path", lambda: latest)

    assert resolve_dataset_path(None, use_latest=True) == latest


def test_download_listing_images_skips_failed_urls(monkeypatch, tmp_path):
    class DummyResponse:
        content = b"ok"

        def raise_for_status(self):
            return None

    calls = {"count": 0}

    def fake_get(url, timeout=20):
        calls["count"] += 1
        if calls["count"] == 1:
            return DummyResponse()
        raise requests.RequestException("boom")

    monkeypatch.setattr("src.ai_cooking_review.requests.get", fake_get)

    paths = download_listing_images(
        "591-1",
        ["https://img/1.jpg", "https://img/2.jpg"],
        images_dir=tmp_path,
        max_images=2,
    )

    assert len(paths) == 1
    assert paths[0].exists()


def test_resolve_codex_command_prefers_path_lookup(monkeypatch):
    monkeypatch.setattr("src.ai_cooking_review.shutil.which", lambda name: "C:\\tools\\codex.cmd" if name == "codex" else None)

    assert resolve_codex_command() == "C:\\tools\\codex.cmd"


def test_build_codex_exec_command_wraps_batch_files(monkeypatch):
    monkeypatch.setattr("src.ai_cooking_review.resolve_codex_command", lambda: "C:\\tools\\codex.cmd")
    monkeypatch.setenv("COMSPEC", "C:\\Windows\\System32\\cmd.exe")

    assert build_codex_exec_command() == [
        "C:\\Windows\\System32\\cmd.exe",
        "/d",
        "/c",
        "C:\\tools\\codex.cmd",
    ]


def test_build_subprocess_run_kwargs_uses_create_no_window_on_windows(monkeypatch):
    monkeypatch.setattr("src.ai_cooking_review.os.name", "nt")
    monkeypatch.setattr("src.ai_cooking_review.subprocess.CREATE_NO_WINDOW", 134217728, raising=False)

    assert build_subprocess_run_kwargs() == {"creationflags": 134217728}
