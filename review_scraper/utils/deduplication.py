from __future__ import annotations

import hashlib
import re
import unicodedata

from utils.output import ReviewRecord


def normalize_for_hash(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def review_hash(record: ReviewRecord) -> str:
    if record.review_id:
        raw = f"{record.source}|review_id|{normalize_for_hash(record.review_id)}"
    else:
        fields = (
            record.source,
            record.product_id,
            record.reviewer_name,
            record.review_date,
            record.review_title,
            record.review_text,
            record.review_rating,
        )
        raw = "|".join(normalize_for_hash(x) for x in fields)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ReviewDeduplicator:
    def __init__(self):
        self.hashes: set[str] = set()

    def seen(self, record: ReviewRecord) -> bool:
        if not record.review_hash:
            record.review_hash = review_hash(record)
        if record.review_hash in self.hashes:
            return True
        self.hashes.add(record.review_hash)
        return False
