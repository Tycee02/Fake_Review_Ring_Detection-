from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd


def validate(path: Path) -> dict:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    report = {
        "file": str(path),
        "rows": len(df),
        "duplicate_review_hashes": int(df["review_hash"].duplicated().sum()) if "review_hash" in df else None,
        "empty_review_text": int((df["review_text"].str.strip() == "").sum()) if "review_text" in df else None,
        "invalid_ratings": int((~df["review_rating"].isin(["1", "2", "3", "4", "5", "1.0", "2.0", "3.0", "4.0", "5.0", ""])).sum()) if "review_rating" in df else None,
        "missing_source": int((df["source"].str.strip() == "").sum()) if "source" in df else None,
        "missing_product_name": int((df["product_name"].str.strip() == "").sum()) if "product_name" in df else None,
        "malformed_product_urls": int(sum(bool(x) and not urlparse(x).scheme for x in df["product_url"])) if "product_url" in df else None,
        "duplicate_review_ids": int(df["review_id"].duplicated().sum()) if "review_id" in df else None,
        "unique_reviews": int(df["review_hash"].nunique()) if "review_hash" in df else None,
        "rating_distribution": df["review_rating"].value_counts(dropna=False).to_dict() if "review_rating" in df else {},
        "missing_values": {k: int((df[k].str.strip() == "").sum()) for k in df.columns},
    }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate(args.csv)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
