from utils.deduplication import review_hash, ReviewDeduplicator
from utils.output import ReviewRecord


def record(text="Great product"):
    return ReviewRecord(source="jumia", product_id="P1", review_text=text, reviewer_name="A", review_date="2026-01-01")


def test_same_record_same_hash():
    assert review_hash(record()) == review_hash(record())


def test_deduplicator():
    d = ReviewDeduplicator()
    assert d.seen(record()) is False
    assert d.seen(record()) is True
