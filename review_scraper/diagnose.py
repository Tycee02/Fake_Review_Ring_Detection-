"""
Run this first on a live machine before a large collection.

It verifies:
- HTTP reachability
- robots.txt
- product-page retrieval
- basic HTML/JSON-LD availability
- Jumia review-link discovery
- Konga Customer Feedback presence

It intentionally does not bypass blocking or access controls.
"""
from __future__ import annotations

import argparse
import urllib.robotparser
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from scrapers.jumia import JumiaScraper
from scrapers.konga import KongaScraper


def check_robots(base: str, ua: str) -> None:
    rp = urllib.robotparser.RobotFileParser(urljoin(base, "/robots.txt"))
    try:
        rp.read()
        print(f"ROBOTS {base}: can_fetch={rp.can_fetch(ua, base)}")
    except Exception as exc:
        print(f"ROBOTS {base}: unable to verify ({exc})")


def inspect(url: str, site: str) -> None:
    ua = "MSc-Research-Review-Collector/1.0"
    with httpx.Client(follow_redirects=True, timeout=25, headers={"User-Agent": ua}) as client:
        r = client.get(url)
        print(f"{site}: status={r.status_code} final={r.url} bytes={len(r.content)}")
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        print("  title:", soup.title.get_text(" ", strip=True) if soup.title else None)
        print("  JSON-LD blocks:", len(soup.select('script[type="application/ld+json"]')))
        print("  links:", len(soup.select("a[href]")))
        if site == "jumia":
            review_links = [a.get("href") for a in soup.select("a[href]") if "productratingsreviews" in a.get("href", "")]
            print("  Jumia review links:", review_links[:5])
        else:
            feedback = [x for x in soup.find_all(string=lambda s: s and "customer feedback" in s.lower())]
            print("  Konga Customer Feedback markers:", len(feedback))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jumia-product")
    p.add_argument("--konga-product")
    args = p.parse_args()

    if args.jumia_product:
        check_robots("https://www.jumia.com.ng", "MSc-Research-Review-Collector/1.0")
        inspect(args.jumia_product, "jumia")

    if args.konga_product:
        check_robots("https://www.konga.com", "MSc-Research-Review-Collector/1.0")
        inspect(args.konga_product, "konga")


if __name__ == "__main__":
    main()
