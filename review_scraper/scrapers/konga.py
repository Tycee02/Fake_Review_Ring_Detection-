
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import httpx

from scrapers.base import BaseScraper
from utils.output import ReviewRecord
from utils.parsing import clean_text, parse_rating, product_id_from_url


class KongaScraper(BaseScraper):
    site = "konga"
    base_url = "https://www.konga.com"
    graphql_endpoint = "https://az-staging-api.konga.com/v1/graphql"

    def discover_product_urls(self):
        """Read Konga product URLs from the research CSV."""

        url_file = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "raw"
            / "konga_product_urls.csv"
        )

        if not url_file.exists():
            self.log.warning(
                "[KONGA] Product URL file not found: %s",
                url_file,
            )
            return

        try:
            with url_file.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as file:

                reader = csv.DictReader(file)

                for row in reader:
                    product_url = (
                        row.get("product_url") or ""
                    ).strip()

                    category = (
                        row.get("category") or ""
                    ).strip()

                    if not product_url:
                        continue

                    yield product_url, category or None

        except Exception as exc:
            self.log.warning(
                "[KONGA] Product URL file could not be read: %s",
                exc,
            )

    def scrape_product(
        self,
        product_url: str,
        category: str | None,
    ) -> list[ReviewRecord]:

        product_id = product_id_from_url(product_url)

        if not product_id:
            self.log.warning(
                "[KONGA] Could not determine product ID: %s",
                product_url,
            )
            return []

        try:
            product_id_int = int(product_id)

        except ValueError:
            self.log.warning(
                "[KONGA] Invalid product ID: %s",
                product_id,
            )
            return []

        product = self._get_product_from_graphql(
            product_id_int
        )

        if not product:
            return []

        records = self._extract_graphql_reviews(
            product,
            product_url,
            category,
        )

        self.log.info(
            "[KONGA] product=%s reviews_found=%d",
            product_id,
            len(records),
        )

        return records[
            : self.settings.max_reviews_per_product
        ]

    def _get_product_from_graphql(
        self,
        product_id: int,
    ) -> dict | None:

        query = """
        {
          product(product_id: %d) {
            product_id
            name
            product_reviews {
              merchant_id
              quality_rating
              communication_rating
              customer_id
              customer_name
              comment
              created_at
              status
              rating_id
              source
            }
          }
        }
        """ % product_id

        headers = {
            "Content-Type": "application/json",
            "x-app-source": "kongavthree",
            "x-app-version": "2.0",
            "X-Skip-Auth": "true",
        }

        try:
            response = httpx.post(
                self.graphql_endpoint,
                json={"query": query},
                headers=headers,
                timeout=30,
            )

            response.raise_for_status()

            payload = response.json()

        except Exception as exc:
            self.log.warning(
                "[KONGA] GraphQL request failed: %s",
                exc,
            )
            return None

        if payload.get("errors"):
            self.log.warning(
                "[KONGA] GraphQL errors: %s",
                payload["errors"],
            )
            return None

        return (
            payload
            .get("data", {})
            .get("product")
        )

    def _extract_graphql_reviews(
        self,
        product: dict,
        product_url: str,
        category: str | None,
    ) -> list[ReviewRecord]:

        product_id = str(
            product.get("product_id")
            or product_id_from_url(product_url)
            or ""
        )

        product_name = product.get("name") or ""

        reviews = product.get(
            "product_reviews",
            [],
        )

        records = []

        for index, review in enumerate(reviews):

            customer_id = review.get("customer_id")
            customer_name = review.get("customer_name")
            comment = review.get("comment") or ""
            rating = review.get("quality_rating")
            created_at = review.get("created_at")

            review_date = self._unix_timestamp_to_iso(
                created_at
            )

            reviewer_name = (
                str(customer_id)
                if customer_id is not None
                else (
                    str(customer_name)
                    if customer_name
                    else f"unknown_{index}"
                )
            )

            review_id = (
                str(review.get("rating_id"))
                if review.get("rating_id")
                else self._make_review_id(
                    product_id,
                    reviewer_name,
                    created_at,
                    index,
                )
            )

            records.append(
                ReviewRecord(
                    source="konga",
                    product_id=product_id,
                    product_name=product_name,
                    product_url=product_url,
                    product_category=category,
                    review_id=review_id,
                    review_text=clean_text(comment),
                    review_rating=parse_rating(rating),
                    review_date=review_date,
                    reviewer_name=reviewer_name,
                )
            )

        return records

    @staticmethod
    def _unix_timestamp_to_iso(value):

        if value is None:
            return None

        try:
            timestamp = int(value)

            return datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc,
            ).isoformat()

        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            return None

    @staticmethod
    def _make_review_id(
        product_id,
        reviewer_id,
        timestamp,
        index,
    ):

        timestamp_value = (
            str(timestamp)
            if timestamp is not None
            else "no_timestamp"
        )

        return (
            f"konga_{product_id}_"
            f"{reviewer_id}_"
            f"{timestamp_value}_"
            f"{index}"
        )
