# Dissertation-ready data collection note

## Data collection implementation

The data collection system is implemented as a modular Python scraper with separate
adapters for Jumia Nigeria and Konga. The adapters share common HTTP handling,
normalization, deduplication, checkpointing, logging, output and validation components.

The collection process begins with public product discovery. Discovered product URLs are
canonicalized and queued. For each product, available product metadata and publicly
displayed textual customer reviews are extracted. Review records are normalized into a
common schema while preserving the original review language, punctuation, spelling and
emojis.

A SHA-256 review hash is generated for every record. Where a platform exposes a reliable
review identifier, that identifier is incorporated into the deduplication key; otherwise,
the hash is derived from normalized source, product, reviewer, date, title, text and
rating fields. Existing hashes are reloaded when collection is resumed.

To support broad product coverage, a configurable maximum number of reviews per product
is enforced. This prevents a highly reviewed product from consuming the complete
collection target. The resulting category and product distribution is retained as
metadata so that the sampling procedure can be reported transparently.

Collection uses persistent HTTP sessions, conservative concurrency, randomized delays,
bounded retries and exponential backoff for transient failures. The system does not
attempt to bypass CAPTCHAs, authentication, access controls or bot-protection mechanisms.

Records are written incrementally to CSV and progress is checkpointed. Consequently,
interruption of the collection process does not require the entire dataset to be
collected again. A validation stage checks duplicate hashes, empty review text, ratings,
URLs, source values, dates, identifiers and missing values.

The final dataset consists of separate Jumia and Konga CSV files and a combined dataset.
Machine-readable summary and provenance metadata are generated for each collection run.
