from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from config import Settings
from scrapers.base import BaseScraper
from utils.output import ReviewRecord
from utils.parsing import clean_text, extract_json_ld, first_json_ld, parse_date, parse_rating, product_id_from_url


class JumiaScraper(BaseScraper):
    site = "jumia"
    base_url = "https://www.jumia.com.ng"
    category_seed = "https://www.jumia.com.ng/mlp-all-categories/"

    # These are deliberately broad/fallback selectors. They must be validated by
    # the local fixture/diagnostic command before a production run.
    PRODUCT_LINK_SELECTORS = [
        'a[href*=".html"]',
        'a[href*="/product/"]',
    ]

    def discover_product_urls(self):
        response = self.http.get(self.category_seed)
        soup = BeautifulSoup(response.text, "lxml")
        seen = set()

        # Discover category/listing links first.
        listing_urls = {self.category_seed}
        for a in soup.select("a[href]"):
            href = a.get("href")
            if not href:
                continue
            full = urljoin(self.base_url, href)
            if self._looks_like_listing(full):
                listing_urls.add(full)

        for listing in listing_urls:
            try:
                page = self.http.get(listing)
            except Exception:
                continue
            psoup = BeautifulSoup(page.text, "lxml")
            category = self._category_from_breadcrumb(psoup)
            for a in psoup.select("a[href]"):
                href = a.get("href")
                if not href:
                    continue
                full = urljoin(self.base_url, href)
                if self._looks_like_product(full) and full not in seen:
                    seen.add(full)
                    yield full, category

    def _looks_like_product(self, url: str) -> bool:
        path = urlparse(url).path
        return bool(re.search(r"-\d+\.html$", path)) and "/catalog/" not in path

    def _looks_like_listing(self, url: str) -> bool:
        path = urlparse(url).path
        return any(token in path for token in ("/catalog/", "/mlp-"))

    def _category_from_breadcrumb(self, soup: BeautifulSoup) -> str | None:
        candidates = soup.select("nav a, [aria-label*='breadcrumb' i] a, .breadcrumb a")
        texts = [clean_text(a.get_text(" ", strip=True)) for a in candidates]
        texts = [x for x in texts if x]
        return texts[-1] if texts else None

    def scrape_product(self, product_url: str, category: str | None) -> list[ReviewRecord]:
        response = self.http.get(product_url)
        soup = BeautifulSoup(response.text, "lxml")
        product = self._product_metadata(soup, product_url, category)
        review_url = self._review_url(soup, product_url)
        if not review_url:
            self.log.warning("[JUMIA] No dedicated review URL found: %s", product_url)
            return []

        records: list[ReviewRecord] = []
        page_no = 1
        while len(records) < self.settings.max_reviews_per_product:
            url = self._page_url(review_url, page_no)
            page = self.http.get(url)
            page_soup = BeautifulSoup(page.text, "lxml")
            page_records = self._extract_reviews(page_soup, product)
            if not page_records:
                break
            records.extend(page_records)
            if not self._has_next_page(page_soup, page_no):
                break
            page_no += 1
        return records[: self.settings.max_reviews_per_product]

    def _product_metadata(self, soup: BeautifulSoup, url: str, category: str | None) -> dict:
        ld = first_json_ld(soup, "Product") or {}
        offers = ld.get("offers") if isinstance(ld.get("offers"), dict) else {}
        agg = ld.get("aggregateRating") if isinstance(ld.get("aggregateRating"), dict) else {}

        name = clean_text(ld.get("name")) or self._meta_content(soup, "og:title")
        brand = ld.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")
        sku = clean_text(ld.get("sku")) or self._sku_from_review_link(soup)

        return {
            "source": self.site,
            "product_id": sku or product_id_from_url(url),
            "product_name": name,
            "product_url": url,
            "product_category": category,
            "product_subcategory": None,
            "brand": clean_text(brand),
            "current_price": clean_text(offers.get("price")),
            "original_price": None,
            "discount": None,
            "average_product_rating": clean_text(agg.get("ratingValue")),
            "product_review_count": clean_text(agg.get("reviewCount")),
        }

    def _review_url(self, soup: BeautifulSoup, product_url: str) -> str | None:
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if "productratingsreviews" in href:
                return urljoin(self.base_url, href)
        return None

    def _sku_from_review_link(self, soup: BeautifulSoup) -> str | None:
        href = self._review_url(soup, "")
        if not href:
            return None
        m = re.search(r"/sku/([^/?#]+)", href)
        return m.group(1) if m else None

    def _page_url(self, review_url: str, page_no: int) -> str:
        parts = urlparse(review_url)
        query = parse_qs(parts.query)
        query["page"] = [str(page_no)]
        return urlunparse(parts._replace(query=urlencode(query, doseq=True)))

    def _extract_reviews(self, soup: BeautifulSoup, product: dict) -> list[ReviewRecord]:
        records = []

        # Prefer structured Review JSON-LD where present.
        for obj in extract_json_ld(soup):
            reviews = obj.get("review")
            if isinstance(reviews, dict):
                reviews = [reviews]
            if not isinstance(reviews, list):
                continue
            for rev in reviews:
                if not isinstance(rev, dict):
                    continue
                author = rev.get("author")
                if isinstance(author, dict):
                    author = author.get("name")
                rating = rev.get("reviewRating")
                if isinstance(rating, dict):
                    rating = rating.get("ratingValue")
                records.append(self._record(product, None, rev.get("name"), rev.get("reviewBody"),
                                            rating, rev.get("datePublished"), author, None, None))

        if records:
            return records

        # Fallback selectors. These intentionally use multiple structural candidates.
        containers = soup.select(
            "[data-testid*='review' i], [class*='review' i], [class*='feedback' i]"
        )
        seen_text = set()
        for box in containers:
            text = clean_text(box.get_text(" ", strip=True))
            if not text or text in seen_text:
                continue
            # Do not treat arbitrary review-page containers as reviews unless
            # a rating or a recognizable review signal is present.
            rating = self._find_rating(box)
            if rating is None:
                continue
            title = self._find_text(box, ["h3", "h4", "[class*='title' i]"])
            body = self._find_text(box, ["p", "[class*='content' i]", "[class*='text' i]"])
            if not body:
                body = text
            date = self._find_text(box, ["time", "[class*='date' i]"])
            author = self._find_text(box, ["[class*='author' i]", "[class*='name' i]"])
            verified = "yes" if "verified purchase" in text.lower() else None
            records.append(self._record(product, None, title, body, rating, date, author, verified, None))
            seen_text.add(text)
        return records

    def _find_text(self, box, selectors):
        for selector in selectors:
            node = box.select_one(selector)
            if node:
                return clean_text(node.get_text(" ", strip=True))
        return None

    def _find_rating(self, box):
        for node in box.select("[aria-label], [title]"):
            value = node.get("aria-label") or node.get("title")
            rating = parse_rating(value)
            if rating:
                return rating
        return parse_rating(box.get_text(" ", strip=True))

    def _record(self, product, review_id, title, text, rating, date, author, verified, helpful):
        return ReviewRecord(
            **product,
            review_id=clean_text(review_id),
            review_title=clean_text(title),
            review_text=clean_text(text),
            review_rating=parse_rating(rating),
            review_date=parse_date(date),
            reviewer_name=clean_text(author),
            verified_purchase=verified,
            helpful_count=clean_text(helpful),
            scraped_at=datetime.now(timezone.utc).isoformat(),
            scrape_run_id=self.settings.run_id,
        )

    def _meta_content(self, soup, property_name):
        node = soup.select_one(f'meta[property="{property_name}"]')
        return clean_text(node.get("content")) if node else None

    def _has_next_page(self, soup, current_page: int) -> bool:
        for a in soup.select("a[href]"):
            label = clean_text(a.get_text(" ", strip=True)) or ""
            href = a.get("href", "")
            if "next" in label.lower() or f"page={current_page + 1}" in href:
                return True
        return False
