from bs4 import BeautifulSoup
from utils.parsing import clean_text, parse_rating, product_id_from_url, first_json_ld


def test_clean_text():
    assert clean_text("  hello   world ") == "hello world"


def test_rating():
    assert parse_rating("Rated 4 out of 5") == "4"


def test_product_id():
    assert product_id_from_url("https://www.konga.com/product/test-item-6213143") == "6213143"


def test_json_ld():
    soup = BeautifulSoup("""
    <script type="application/ld+json">
    {"@type":"Product","name":"Test"}
    </script>
    """, "lxml")
    assert first_json_ld(soup, "Product")["name"] == "Test"
