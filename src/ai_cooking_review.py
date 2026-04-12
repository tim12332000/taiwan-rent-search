"""AI-assisted image review for cooking convenience."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from .analysis import cooking_convenience_profile, latest_dataset_path, parse_images
from .case_workspace import (
    build_case_ai_reviews_path,
    build_case_ai_usage_log_path,
    build_case_images_dir,
)


AI_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {
            "type": "string",
            "enum": ["適合煮飯", "可勉強煮", "不適合煮飯", "不確定"],
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reason": {"type": "string"},
        "positive_signals": {"type": "array", "items": {"type": "string"}},
        "negative_signals": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["label", "confidence", "reason", "positive_signals", "negative_signals"],
    "additionalProperties": False,
}


def load_ai_reviews(path: str | Path) -> dict[str, dict[str, object]]:
    review_path = Path(path)
    if not review_path.exists():
        return {}
    try:
        payload = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_ai_reviews(path: str | Path, reviews: dict[str, dict[str, object]]) -> Path:
    review_path = Path(path)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps(reviews, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return review_path


def ai_cooking_label_to_score(label: str) -> int:
    mapping = {
        "適合煮飯": 3,
        "可勉強煮": 2,
        "不確定": 1,
        "不適合煮飯": 0,
    }
    return mapping.get(label, 0)


def image_urls_hash(urls: list[str]) -> str:
    digest = hashlib.sha1()
    for url in urls:
        digest.update(url.encode("utf-8"))
    return digest.hexdigest()[:16]


def build_dataset_ai_reviews_path(dataset_path: str | Path) -> Path:
    return Path(dataset_path).parent / "ai_cooking_reviews.json"


def build_dataset_ai_usage_log_path(dataset_path: str | Path) -> Path:
    return Path(dataset_path).parent / "ai_usage.jsonl"


def build_dataset_images_dir(dataset_path: str | Path) -> Path:
    return Path(dataset_path).parent / "images"


def build_dataset_ai_schema_path(dataset_path: str | Path) -> Path:
    return build_dataset_images_dir(dataset_path) / "ai_review_schema.json"


def write_schema_file(schema_path: str | Path) -> Path:
    schema_path = Path(schema_path)
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(json.dumps(AI_REVIEW_SCHEMA, ensure_ascii=False), encoding="utf-8")
    return schema_path


def append_usage_log(path: str | Path, payload: dict[str, object]) -> Path:
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return log_path


def download_listing_images(
    listing_id: str,
    image_urls: list[str],
    *,
    images_dir: str | Path,
    max_images: int = 4,
) -> list[Path]:
    target_dir = Path(images_dir) / listing_id
    target_dir.mkdir(parents=True, exist_ok=True)
    local_paths: list[Path] = []

    for index, image_url in enumerate(image_urls[:max_images], start=1):
        suffix = Path(urlparse(image_url).path).suffix or ".jpg"
        image_path = target_dir / f"image_{index:02d}{suffix}"
        try:
            if not image_path.exists():
                response = requests.get(image_url, timeout=20)
                response.raise_for_status()
                image_path.write_bytes(response.content)
            local_paths.append(image_path)
        except (OSError, requests.RequestException):
            continue

    return local_paths


def build_codex_prompt(listing: dict[str, str]) -> str:
    title = listing.get("title", "")
    platform = listing.get("platform", "")
    description = listing.get("description", "")
    details = listing.get("detail_facilities", "")
    return (
        "請只根據附加圖片判斷這個租屋物件的可煮飯方便程度。"
        "重點不是有沒有任何洗手台，而是一般租客能不能洗食材、備料、正常煮一餐。"
        "務必排除浴室洗手台、洗面盆、衛浴檯面。"
        f"\n標題：{title}\n來源：{platform}\n描述：{description}\n設備：{details}"
        "\n請輸出符合 schema 的 JSON。"
    )


def resolve_codex_command() -> str:
    command = shutil.which("codex") or shutil.which("codex.cmd") or shutil.which("codex.exe")
    if not command:
        raise FileNotFoundError("找不到 codex CLI，無法執行 AI 看圖。")
    return command


def build_codex_exec_command() -> list[str]:
    command = resolve_codex_command()
    suffix = Path(command).suffix.lower()
    if suffix in {".cmd", ".bat"}:
        cmd_exe = os.environ.get("COMSPEC") or str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "cmd.exe")
        return [cmd_exe, "/d", "/c", command]
    return [command]


def build_subprocess_run_kwargs() -> dict[str, object]:
    kwargs: dict[str, object] = {}
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def run_codex_image_review(
    *,
    image_paths: list[Path],
    listing: dict[str, str],
    schema_path: str | Path,
    workdir: str | Path,
) -> tuple[dict[str, object], dict[str, int]]:
    command = [
        *build_codex_exec_command(),
        "exec",
        "--skip-git-repo-check",
        "--json",
        "--output-schema",
        str(schema_path),
        "-",
    ]
    for image_path in image_paths:
        command.extend(["-i", str(image_path)])

    result = subprocess.run(
        command,
        cwd=workdir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        input=build_codex_prompt(listing),
        **build_subprocess_run_kwargs(),
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Codex image review failed.\nSTDOUT:\n"
            + result.stdout[-4000:]
            + "\nSTDERR:\n"
            + result.stderr[-4000:]
        )

    review: dict[str, object] | None = None
    usage: dict[str, int] = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "item.completed":
            text = payload.get("item", {}).get("text", "")
            try:
                review = json.loads(text)
            except json.JSONDecodeError:
                continue
        if payload.get("type") == "turn.completed":
            usage = payload.get("usage", {})

    if review is None:
        raise RuntimeError("Codex image review did not return a structured result.")

    return review, {
        "input_tokens": int(usage.get("input_tokens") or 0),
        "cached_input_tokens": int(usage.get("cached_input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
    }


def ai_review_candidate_priority(row: dict[str, str]) -> tuple[int, int, str, str]:
    score, _, _ = cooking_convenience_profile(row)
    bucket = 0 if score == 1 else 1 if score == 0 else 2
    return (bucket, score, row.get("platform", ""), row.get("id", ""))


def build_review_record(
    review: dict[str, object],
    *,
    current_hash: str,
    image_count: int,
) -> dict[str, object]:
    return {
        "label": review["label"],
        "score": ai_cooking_label_to_score(str(review["label"])),
        "confidence": review["confidence"],
        "reason": review["reason"],
        "positive_signals": review["positive_signals"],
        "negative_signals": review["negative_signals"],
        "image_urls_hash": current_hash,
        "reviewed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "image_count": image_count,
    }


def review_dataset_images(
    *,
    dataset_path: str | Path,
    review_path: str | Path,
    usage_log_path: str | Path,
    images_dir: str | Path,
    schema_path: str | Path,
    max_listings: int = 12,
    max_images_per_listing: int = 4,
    workdir: str | Path = ".",
    scope_label: str = "",
) -> dict[str, object]:
    dataset_path = Path(dataset_path)
    review_path = Path(review_path)
    usage_log_path = Path(usage_log_path)
    images_dir = Path(images_dir)
    schema_path = write_schema_file(schema_path)
    reviews = load_ai_reviews(review_path)

    with dataset_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    candidates = []
    for row in rows:
        image_urls = parse_images(row.get("images"))
        if not image_urls:
            continue
        priority = ai_review_candidate_priority(row)
        candidates.append((priority, row, image_urls))

    candidates.sort(key=lambda item: item[0])
    reviewed_count = 0
    cached_count = 0

    for _, row, image_urls in candidates[:max_listings]:
        listing_id = row.get("id", "")
        if not listing_id:
            continue
        current_hash = image_urls_hash(image_urls[:max_images_per_listing])
        cached = reviews.get(listing_id)
        if cached and cached.get("image_urls_hash") == current_hash:
            cached_count += 1
            continue

        local_images = download_listing_images(
            listing_id,
            image_urls,
            images_dir=images_dir,
            max_images=max_images_per_listing,
        )
        if not local_images:
            continue
        review, usage = run_codex_image_review(
            image_paths=local_images,
            listing=row,
            schema_path=schema_path,
            workdir=workdir,
        )
        reviews[listing_id] = build_review_record(
            review,
            current_hash=current_hash,
            image_count=len(local_images),
        )
        append_usage_log(
            usage_log_path,
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "listing_id": listing_id,
                "scope": scope_label or dataset_path.parent.name,
                "dataset": str(dataset_path),
                "image_count": len(local_images),
                **usage,
            },
        )
        reviewed_count += 1

    save_ai_reviews(review_path, reviews)
    return {
        "review_path": str(review_path),
        "usage_log_path": str(usage_log_path),
        "reviewed_count": reviewed_count,
        "cached_count": cached_count,
        "total_cached_items": len(reviews),
    }


def review_listing_in_dataset(
    *,
    dataset_path: str | Path,
    listing_id: str,
    max_images_per_listing: int = 4,
    workdir: str | Path = ".",
) -> dict[str, object]:
    dataset_path = Path(dataset_path)
    review_path = build_dataset_ai_reviews_path(dataset_path)
    usage_log_path = build_dataset_ai_usage_log_path(dataset_path)
    images_dir = build_dataset_images_dir(dataset_path)
    schema_path = write_schema_file(build_dataset_ai_schema_path(dataset_path))
    reviews = load_ai_reviews(review_path)

    with dataset_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    row = next((candidate for candidate in rows if candidate.get("id", "") == listing_id), None)
    if row is None:
        raise ValueError("找不到指定房源。")

    image_urls = parse_images(row.get("images"))
    if not image_urls:
        raise ValueError("這筆房源沒有可供 AI 審核的圖片。")

    current_hash = image_urls_hash(image_urls[:max_images_per_listing])
    cached = reviews.get(listing_id)
    if cached and cached.get("image_urls_hash") == current_hash:
        return {
            "listing_id": listing_id,
            "review_path": str(review_path),
            "usage_log_path": str(usage_log_path),
            "review": cached,
            "cached": True,
        }

    local_images = download_listing_images(
        listing_id,
        image_urls,
        images_dir=images_dir,
        max_images=max_images_per_listing,
    )
    if not local_images:
        raise ValueError("這筆房源的圖片目前無法下載，稍後再試。")

    review, usage = run_codex_image_review(
        image_paths=local_images,
        listing=row,
        schema_path=schema_path,
        workdir=workdir,
    )
    review_record = build_review_record(
        review,
        current_hash=current_hash,
        image_count=len(local_images),
    )
    reviews[listing_id] = review_record
    save_ai_reviews(review_path, reviews)
    append_usage_log(
        usage_log_path,
        {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "listing_id": listing_id,
            "scope": dataset_path.parent.name,
            "dataset": str(dataset_path),
            "image_count": len(local_images),
            **usage,
        },
    )
    return {
        "listing_id": listing_id,
        "review_path": str(review_path),
        "usage_log_path": str(usage_log_path),
        "review": review_record,
        "cached": False,
        "usage": usage,
    }


def review_dataset_images_in_place(
    *,
    dataset_path: str | Path,
    max_listings: int = 12,
    max_images_per_listing: int = 4,
    workdir: str | Path = ".",
) -> dict[str, object]:
    dataset_path = Path(dataset_path)
    return review_dataset_images(
        dataset_path=dataset_path,
        review_path=build_dataset_ai_reviews_path(dataset_path),
        usage_log_path=build_dataset_ai_usage_log_path(dataset_path),
        images_dir=build_dataset_images_dir(dataset_path),
        schema_path=build_dataset_ai_schema_path(dataset_path),
        max_listings=max_listings,
        max_images_per_listing=max_images_per_listing,
        workdir=workdir,
        scope_label=dataset_path.parent.name,
    )


def review_case_dataset_images(
    *,
    dataset_path: str | Path,
    case_slug: str,
    base_dir: str | Path = "data/cases",
    max_listings: int = 12,
    max_images_per_listing: int = 4,
    workdir: str | Path = ".",
) -> dict[str, object]:
    return review_dataset_images(
        dataset_path=dataset_path,
        review_path=build_case_ai_reviews_path(case_slug, base_dir),
        usage_log_path=build_case_ai_usage_log_path(case_slug, base_dir),
        images_dir=build_case_images_dir(case_slug, base_dir),
        schema_path=build_case_images_dir(case_slug, base_dir) / "ai_review_schema.json",
        max_listings=max_listings,
        max_images_per_listing=max_images_per_listing,
        workdir=workdir,
        scope_label=case_slug,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="對資料集執行 AI 看圖快取，並可選擇刷新搜尋頁。")
    parser.add_argument("--input", help="資料集 CSV 路徑，預設使用最新資料集")
    parser.add_argument("--latest", action="store_true", help="直接使用 data/ 下最新資料集")
    parser.add_argument("--max-listings", type=int, default=8, help="最多評幾筆候選")
    parser.add_argument("--max-images", type=int, default=3, help="每筆最多送幾張圖")
    parser.add_argument("--refresh-search-app", action="store_true", help="完成後同步刷新搜尋頁")
    return parser.parse_args()


def resolve_dataset_path(input_path: str | None, use_latest: bool) -> Path:
    if input_path:
        return Path(input_path)
    if use_latest or not input_path:
        return latest_dataset_path()
    raise ValueError("無法決定資料集路徑。")


def main() -> None:
    args = parse_args()
    dataset_path = resolve_dataset_path(args.input, args.latest)
    summary = review_dataset_images_in_place(
        dataset_path=dataset_path,
        max_listings=args.max_listings,
        max_images_per_listing=args.max_images,
    )
    if args.refresh_search_app:
        from .webapp import export_search_app

        export_search_app(dataset_path)

    print(f"Dataset: {dataset_path}")
    print(f"AI review cache: {summary['review_path']}")
    print(f"AI usage log: {summary['usage_log_path']}")
    print(f"AI reviewed this run: {summary['reviewed_count']}")
    print(f"AI cache hits this run: {summary['cached_count']}")


if __name__ == "__main__":
    main()
