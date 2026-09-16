from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = BeautifulSoup(str(value), "lxml").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def absolute_url(base: str, href: str | None) -> str | None:
    if not href:
        return None
    return urljoin(base, href)


def extract_json_ld(soup: BeautifulSoup) -> list[dict]:
    results = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            obj = json.loads(script.string or script.get_text())
            if isinstance(obj, list):
                results.extend(x for x in obj if isinstance(x, dict))
            elif isinstance(obj, dict):
                results.append(obj)
        except (json.JSONDecodeError, TypeError):
            continue
    return results


def first_json_ld(soup: BeautifulSoup, typ: str) -> dict | None:
    for obj in extract_json_ld(soup):
        value = obj.get("@type")
        types = value if isinstance(value, list) else [value]
        if typ in types:
            return obj
    return None


def parse_rating(value: Any) -> str | None:
    if value is None:
        return None
    match = re.search(r"(?<!\d)([1-5](?:[.,]\d+)?)\s*(?:/|out of)?\s*5?", str(value))
    return match.group(1).replace(",", ".") if match else None


def parse_date(value: Any) -> str | None:
    if not value:
        return None
    text = clean_text(value)
    if not text:
        return None
    try:
        from dateutil import parser
        return parser.parse(text, fuzzy=True).isoformat()
    except Exception:
        return text


def product_id_from_url(url: str) -> str | None:
    path = urlparse(url).path.rstrip("/")
    m = re.search(r"(\d+)(?:\.html)?$", path)
    return m.group(1) if m else None


def normalize_category(value: str | None) -> str | None:
    return clean_text(value)
