from __future__ import annotations

import argparse
import logging
from pathlib import Path

from config import Settings
from scrapers.jumia import JumiaScraper
from scrapers.konga import KongaScraper
from utils.logging_utils import configure_logging


def build_scraper(site: str, settings: Settings):
    if site == "jumia":
        return JumiaScraper(settings)
    if site == "konga":
        return KongaScraper(settings)
    raise ValueError(f"Unsupported site: {site}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Research-grade Jumia/Konga review collector")
    parser.add_argument("--site", choices=["jumia", "konga", "all"], default="all")
    parser.add_argument("--target", type=int, default=5000)
    parser.add_argument("--max-reviews-per-product", type=int, default=100)
    parser.add_argument("--max-products", type=int, default=0, help="0 means no explicit product limit")
    parser.add_argument("--categories", nargs="*", default=None)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--headless", action="store_true", help="Reserved for browser fallback; HTTP remains default")
    parser.add_argument("--product-url", default=None, help="Optional seed product URL")
    parser.add_argument("--output-dir", default="data")
    args = parser.parse_args()

    if args.concurrency < 1 or args.concurrency > 5:
        parser.error("--concurrency must be between 1 and 5")

    settings = Settings(
        target_reviews=args.target,
        max_reviews_per_product=args.max_reviews_per_product,
        max_products=args.max_products,
        categories=args.categories,
        delay_seconds=args.delay,
        concurrency=args.concurrency,
        resume=args.resume,
        headless=args.headless,
        seed_product_url=args.product_url,
        output_dir=Path(args.output_dir),
    )
    configure_logging(Path("logs"))
    logging.info("Starting collection: site=%s target=%s", args.site, args.target)

    sites = ["jumia", "konga"] if args.site == "all" else [args.site]
    for site in sites:
        scraper = build_scraper(site, settings)
        scraper.run()

    if args.site == "all":
        from utils.output import combine_site_csvs
        combine_site_csvs(settings.output_dir)


if __name__ == "__main__":
    main()
