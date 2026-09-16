from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone


class Checkpoint:
    def __init__(self, path: Path):
        self.path = path
        self.data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {
                "processed_product_urls": [],
                "queued_product_urls": [],
                "review_hashes": [],
                "current_review_count": 0,
                "failed_urls": [],
                "categories": [],
                "updated_at": None,
            }
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.data["updated_at"] = datetime.now(timezone.utc).isoformat()
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)
