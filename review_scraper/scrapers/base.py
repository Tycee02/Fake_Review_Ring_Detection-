from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urldefrag, urlparse

import httpx

from config import Settings
from utils.checkpoint import Checkpoint
from utils.deduplication import ReviewDeduplicator
from utils.http import HttpClient
from utils.output import ReviewRecord, append_records, write_summary


class BaseScraper(ABC):
    site: str
    base_url: str

    def __init__(self, settings: Settings):
        self.settings = settings
        self.settings.ensure_dirs()
        self.log = logging.getLogger(self.site)
        self.http = HttpClient(settings)
        self.checkpoint = Checkpoint(settings.checkpoint_dir / f"{self.site}.json")
        self.dedup = ReviewDeduplicator()
        self.output_file = settings.output_dir / f"{self.site}_reviews.csv"
        self.failed: list[dict[str, Any]] = []
        self.stats = {
            "source": self.site,
            "target_reviews": settings.target_reviews,
            "unique_reviews": 0,
            "products_processed": 0,
            "products_discovered": 0,
            "categories": [],
            "duplicates_rejected": 0,
            "failed_requests": 0,
        }

        if settings.resume and self.output_file.exists():
            from utils.output import load_existing_hashes
            self.dedup.hashes.update(load_existing_hashes(self.output_file))
            self.stats["unique_reviews"] = len(self.dedup.hashes)

    @abstractmethod
    def discover_product_urls(self) -> Iterable[tuple[str, str | None]]:
        """Yield (product_url, category)."""

    @abstractmethod
    def scrape_product(self, product_url: str, category: str | None) -> list[ReviewRecord]:
        ...

    def canonicalize_url(self, url: str) -> str:
        absolute = urljoin(self.base_url, url)
        absolute, _ = urldefrag(absolute)
        parsed = urlparse(absolute)
        return parsed._replace(fragment="", query="").geturl().rstrip("/")

    def add_records(self, records: list[ReviewRecord]) -> int:
        unique: list[ReviewRecord] = []
        for record in records:
            if not record.review_text or not record.review_text.strip():
                continue
            if self.dedup.seen(record):
                self.stats["duplicates_rejected"] += 1
                continue
            unique.append(record)
            if self.stats["unique_reviews"] + len(unique) >= self.settings.target_reviews:
                break

        if unique:
            append_records(self.output_file, unique)
            self.stats["unique_reviews"] += len(unique)
        return len(unique)

    def run(self) -> None:
        self.log.info("[%s] Starting run_id=%s", self.site.upper(), self.settings.run_id)
        product_iter = self.discover_product_urls()
        seen_products = set(self.checkpoint.data.get("processed_product_urls", []))

        for product_url, category in product_iter:
            self.stats["products_discovered"] += 1

            if self.stats["unique_reviews"] >= self.settings.target_reviews:
                break
            product_url = self.canonicalize_url(product_url)
            if product_url in seen_products:
                continue
            if self.settings.max_products and self.stats["products_processed"] >= self.settings.max_products:
                break

            try:
                records = self.scrape_product(product_url, category)
                added = self.add_records(records)
                self.log.info(
                    "[%s] Product %s | +%d unique | total %d/%d",
                    self.site.upper(), product_url, added,
                    self.stats["unique_reviews"], self.settings.target_reviews
                )
            except Exception as exc:
                self.stats["failed_requests"] += 1
                self.failed.append({
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "website": self.site,
                    "url": product_url,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                })
                self.log.exception("[%s] Product failed: %s", self.site.upper(), product_url)
            finally:
                seen_products.add(product_url)
                self.stats["products_processed"] += 1
                self.checkpoint.data["processed_product_urls"] = list(seen_products)
                self.checkpoint.data["current_review_count"] = self.stats["unique_reviews"]
                self.checkpoint.data["failed_urls"] = self.failed
                self.checkpoint.save()

            if self.stats["unique_reviews"] % max(1, self.settings.checkpoint_every_reviews) == 0:
                self.checkpoint.save()

        summary_path = self.settings.output_dir / f"{self.site}_summary.json"
        write_summary(summary_path, self.stats)
        self.log.info("[%s] Finished: %s", self.site.upper(), self.stats)


def text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    value = " ".join(str(value).split())
    return value or None
