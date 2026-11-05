# Phase II(b) MongoDB loading

Place these files together in a MongoDB folder in your repo. `util.py` is an unchanged copy of the uploaded Phase I helpers. The actual repo and branch were not supplied.

## Document model

`products` has one document per cleaned `parent_asin`, stored as the string `_id`. Fields are `title`, `main_category`, and `store` (string/null), `average_rating` and `price` (Decimal128/null), `rating_number` (Int64/null), `categories`, `description`, and `features` (array/null), and `details` (document/null). Nested types follow the source, after Phase I cleaning.

`reviews` has a document `_id` containing `source_id` (string) and `source_line` (Int64), always constructed in that order. Other fields are `parent_asin`, `user_id`, `asin`, `title`, and `review_text` (string/null, with parent required), `rating` (Decimal128/null), `reviewed_at` (UTC BSON date/null), `helpful_vote` (Int64/null), and `verified_purchase` (boolean/null).

Each collection has its automatic unique `_id` index. The loader creates a nonunique `reviews.parent_asin` index after importing, supporting product-to-review lookups. Review-to-product lookups use `products._id`. Additional workload indexes can follow when team queries are available.

Product metadata arrays and details are embedded. Reviews reference products because the number of reviews per product is unbounded. Images, videos, author, subtitle, and bought_together remain excluded, matching Phase I. This model is defined by document construction in Python; it does not install server-side schema validators or foreign keys.

## Run

Install the driver and start your local MongoDB server.

```bash
python3 -m pip install pymongo
python3 load_mongodb.py --database amazon_electronics_test --data-folder "/path/to/Amazon Electronics Dataset" --limit 1000
```

This reads through physical line 1,000 in each file. Blank lines do not count in the printed scanned total but retain their place in source-line numbering. Inspect the small import in mongosh.

```javascript
use amazon_electronics_test
db.products.countDocuments({})
db.reviews.countDocuments({})
db.products.findOne()
db.reviews.findOne()
db.reviews.getIndexes()
```

Rerun the same command. Inserted counts should be zero and existing records remain unchanged. Identical review content on different source lines is retained, matching MySQL's identity rule.

For the full import, use a separate database without `--limit`.

```bash
python3 load_mongodb.py --data-folder "/path/to/Amazon Electronics Dataset"
```

To match a MySQL database whose unmatched reviews were removed, use a fresh database with matching enabled.

```bash
python3 load_mongodb.py --database amazon_electronics_matched --data-folder "/path/to/Amazon Electronics Dataset" --require-product
```

The default retains reviews with usable parent keys even when metadata is absent, matching MySQL when the entire cleanup function is skipped. The optional flag queries matching product IDs once per batch. It does not remove unmatched reviews already inserted by a previous run. Keep the mode fixed per database. With limited metadata, a matched sample may exclude reviews whose metadata occurs later in the source file.

## Counts and failures

Each collection prints scanned, inserted, duplicate, missing_parent, invalid, and unmatched_product counts. Invalid counts malformed JSON and non-object input. Optional invalid field values become null under Phase I rules. Skipped records are the sum of duplicate, missing_parent, and unmatched_product. Blank lines are ignored. Decimal fields use two places with half-up rounding to approximate MySQL DECIMAL storage; verify parity on the actual MySQL server before benchmarking.

Unexpected BSON encoding errors, oversized documents, and database failures stop the import rather than silently excluding records. Earlier completed writes remain saved. Duplicate IDs are ignored, so restarting with the same unchanged source files is safe. Run one loader per target database to preserve first-occurrence metadata deterministically. Do not reorder or edit the JSONL files between reruns.

MongoDB key matching is binary by default. The SQL schema does not explicitly set collation; check actual MySQL collation and identifier lengths before claiming exact parity. Reconcile identities and cleaned values before benchmark timing, using the same raw source versions and matching mode. This loader does not verify the population in your existing MySQL database.
