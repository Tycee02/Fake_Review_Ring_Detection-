# Jumia/Konga Research Review Scraper

A conservative Python 3.11+ collection system for the MSc research dataset:

- Jumia Nigeria
- Konga

Target: up to 5,000 unique textual customer reviews per site.

## Important research note

This repository is deliberately designed so that the first run is a **diagnostic/proof-of-concept run**, not an immediate 10,000-review crawl.

The current public websites can change. Selector/DOM assumptions must therefore be verified on the machine executing the scraper before a full run.

The scraper does not:
- bypass CAPTCHAs;
- bypass authentication;
- evade bot protection;
- rotate identities/proxies to evade blocking;
- access private APIs;
- invent missing review fields.

If access is denied or the site changes, the failure is logged rather than silently fabricated.

## Architecture

```text
main.py
  |
  +-- JumiaScraper
  |     +-- category/listing discovery
  |     +-- product metadata
  |     +-- dedicated review URL
  |     +-- numbered review pages
  |
  +-- KongaScraper
        +-- sitemap discovery
        +-- product metadata
        +-- Customer Feedback extraction

        -> ReviewRecord
        -> SHA-256 deduplication
        -> checkpoint
        -> CSV
        -> validation
```

## Installation

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 1. Diagnose first

Supply one current product URL from each website.

```bash
python diagnose.py \
  --jumia-product "PASTE_CURRENT_JUMIA_PRODUCT_URL" \
  --konga-product "PASTE_CURRENT_KONGA_PRODUCT_URL"
```

Do not proceed to the large crawl until:
- both pages return successfully;
- robots.txt can be checked;
- Jumia review-link discovery is confirmed;
- Konga Customer Feedback behaviour is inspected.

## 2. Small proof of concept

Start with 10 reviews/site.

```bash
python main.py --site jumia --target 10 --max-reviews-per-product 5 --max-products 10
python main.py --site konga --target 10 --max-reviews-per-product 5 --max-products 10
```

Inspect the CSVs manually.

## 3. Full collection

After validating the proof of concept:

```bash
python main.py --site all --target 5000 \
  --max-reviews-per-product 100 \
  --concurrency 3 \
  --delay 2 \
  --resume
```

The target is per site when `--site jumia` or `--site konga` is used.

## Output

```text
data/
  jumia_reviews.csv
  konga_reviews.csv
  combined_reviews.csv
  jumia_summary.json
  konga_summary.json

checkpoints/
  jumia.json
  konga.json

logs/
  scraper.log
  errors.log
```

## Resume

```bash
python main.py --site all --target 5000 --resume
```

Previously processed product URLs and existing review hashes are loaded.

## Validation

```bash
python validate.py data/jumia_reviews.csv --output data/jumia_validation.json
python validate.py data/konga_reviews.csv --output data/konga_validation.json
```

The validator reports duplicates, empty review text, invalid ratings, malformed URLs, missing fields, rating distribution and missing-value counts. It does not silently delete suspicious records.

## Anonymization

Raw and anonymized datasets should be kept separately.

```bash
python anonymize.py \
  data/jumia_reviews.csv \
  data/jumia_reviews_anonymized.csv \
  --salt "REPLACE_WITH_A_PRIVATE_RESEARCH_SALT"
```

Do not commit the salt to Git.

## CSV schema

The normalized schema is:

- source
- product_id
- product_name
- product_url
- product_category
- product_subcategory
- brand
- current_price
- original_price
- discount
- average_product_rating
- product_review_count
- review_id
- review_title
- review_text
- review_rating
- review_date
- reviewer_name
- verified_purchase
- helpful_count
- scraped_at
- scrape_run_id
- review_hash

## Sampling

The scraper has a configurable per-product cap to reduce domination by a single highly reviewed product.

This is a collection constraint, not a claim that the resulting dataset is statistically representative of all Nigerian e-commerce reviews. The dissertation should report the actual category/product distribution.

## Ethical collection

The collection is limited to publicly displayed product/review information needed for the research. It does not attempt to discover additional information about reviewers.

Before collection, inspect the current robots.txt and applicable website terms/policies. Use low concurrency and delays. Stop/reduce collection if automated access is blocked.

## Known limitations

1. Website HTML structures can change.
2. Konga review pagination/API behaviour requires live verification on the machine running the scraper.
3. Some products may expose no textual reviews even when a product exists.
4. Aggregate product ratings are not treated as individual reviews.
5. The scraper cannot guarantee 5,000 records if the publicly accessible source does not contain that many usable reviews or access is restricted.
6. The current implementation intentionally avoids undocumented/private API access.

## Dissertation provenance

Record:
- scrape date/time;
- scraper run ID;
- target;
- actual count;
- products/categories represented;
- per-product cap;
- software version;
- collection settings;
- failures;
- validation report.

These metadata support reproducibility of the dataset construction process.
