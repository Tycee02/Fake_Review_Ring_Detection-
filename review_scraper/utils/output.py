from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


COLUMNS = [
    "source", "product_id", "product_name", "product_url",
    "product_category", "product_subcategory", "brand",
    "current_price", "original_price", "discount",
    "average_product_rating", "product_review_count",
    "review_id", "review_title", "review_text", "review_rating",
    "review_date", "reviewer_name", "verified_purchase",
    "helpful_count", "scraped_at", "scrape_run_id", "review_hash",
]


@dataclass
class ReviewRecord:
    source: str
    product_id: str | None = None
    product_name: str | None = None
    product_url: str | None = None
    product_category: str | None = None
    product_subcategory: str | None = None
    brand: str | None = None
    current_price: str | None = None
    original_price: str | None = None
    discount: str | None = None
    average_product_rating: str | None = None
    product_review_count: str | None = None
    review_id: str | None = None
    review_title: str | None = None
    review_text: str | None = None
    review_rating: str | None = None
    review_date: str | None = None
    reviewer_name: str | None = None
    verified_purchase: str | None = None
    helpful_count: str | None = None
    scraped_at: str | None = None
    scrape_run_id: str | None = None
    review_hash: str | None = None


def append_records(path: Path, records: list[ReviewRecord]) -> None:
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def load_existing_hashes(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        df = pd.read_csv(path, usecols=["review_hash"], dtype=str)
        return set(df["review_hash"].dropna().tolist())
    except Exception:
        return set()


def combine_site_csvs(output_dir: Path) -> None:
    paths = [output_dir / "jumia_reviews.csv", output_dir / "konga_reviews.csv"]
    frames = [pd.read_csv(p, dtype=str) for p in paths if p.exists()]
    if frames:
        pd.concat(frames, ignore_index=True).drop_duplicates(subset=["review_hash"]).to_csv(
            output_dir / "combined_reviews.csv", index=False, encoding="utf-8"
        )


def write_summary(path: Path, stats: dict[str, Any]) -> None:
    payload = dict(stats)
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
