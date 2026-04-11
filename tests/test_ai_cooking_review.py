import json
from pathlib import Path

from src.ai_cooking_review import ai_cooking_label_to_score, image_urls_hash, load_ai_reviews, save_ai_reviews


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
