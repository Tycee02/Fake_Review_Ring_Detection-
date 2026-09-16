from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import platform
import uuid


@dataclass
class Settings:
    target_reviews: int = 5000
    max_reviews_per_product: int = 100
    max_products: int = 0
    categories: list[str] | None = None
    delay_seconds: float = 2.0
    concurrency: int = 3
    resume: bool = False
    headless: bool = False
    seed_product_url: str | None = None

    output_dir: Path = Path("data")
    checkpoint_dir: Path = Path("checkpoints")
    log_dir: Path = Path("logs")

    timeout_seconds: float = 25.0
    max_retries: int = 3
    checkpoint_every_reviews: int = 100
    checkpoint_every_products: int = 25

    user_agent: str = field(default_factory=lambda:
        os.getenv(
            "SCRAPER_USER_AGENT",
            "MSc-Research-Review-Collector/1.0 (+research-contact-required)"
        )
    )
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    python_version: str = field(default_factory=platform.python_version)
    schema_version: str = "1.0"

    def ensure_dirs(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
