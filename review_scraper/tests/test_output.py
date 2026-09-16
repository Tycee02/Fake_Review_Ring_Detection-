from pathlib import Path
from utils.output import ReviewRecord, append_records, load_existing_hashes


def test_csv_output(tmp_path: Path):
    path = tmp_path / "reviews.csv"
    r = ReviewRecord(source="jumia", product_name="X", review_text="Good", review_hash="abc")
    append_records(path, [r])
    assert path.exists()
    assert load_existing_hashes(path) == {"abc"}
