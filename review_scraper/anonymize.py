from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd


def anonymize(input_csv: Path, output_csv: Path, salt: str) -> None:
    df = pd.read_csv(input_csv, dtype=str, keep_default_na=False)

    def anon(value: str) -> str:
        raw = f"{salt}|{value}".encode("utf-8")
        return "reviewer_" + hashlib.sha256(raw).hexdigest()[:16]

    if "reviewer_name" in df.columns:
        df["reviewer_name"] = df["reviewer_name"].map(lambda x: anon(x) if x else "")
    df.to_csv(output_csv, index=False, encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("input_csv", type=Path)
    p.add_argument("output_csv", type=Path)
    p.add_argument("--salt", required=True)
    args = p.parse_args()
    anonymize(args.input_csv, args.output_csv, args.salt)
