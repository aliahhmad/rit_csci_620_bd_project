# Phase II(b) — MongoDB Design and Comparison with MySQL

We stored the Amazon Reviews 2023 Electronics dataset in two MongoDB collections, `products` and `reviews`. The final database contains **1,610,012 products** and **43,886,944 reviews**, confirmed using mongosh.

## Collection Structures

Each `products` document stores one product. Its `_id` contains the cleaned `parent_asin` from the source metadata and acts as the product key.

| Fields | BSON type | Purpose |
| --- | --- | --- |
| `_id` | String | Required product key (`parent_asin`) |
| `title`, `main_category`, `store` | String or null | Product name, category, and store |
| `average_rating`, `price` | Decimal128 or null | Metadata average rating and price |
| `rating_number` | Int64 or null | Metadata rating count |
| `categories`, `description`, `features` | Array or null | Embedded product information |
| `details` | Document or null | Embedded attributes, such as manufacturer and color |

Each `reviews` document stores one source review. Its `_id` is an embedded document containing `source_id` and `source_line`, preserving the combined review key used in MySQL.

| Fields | BSON type | Purpose |
| --- | --- | --- |
| `_id` | Document | Required combined review key |
| `_id.source_id` | String | Required dataset identifier |
| `_id.source_line` | Int64 | Required original JSONL line number |
| `parent_asin` | String | Required reference to `products._id` |
| `user_id`, `asin` | String or null | Reviewer and reviewed item identifiers |
| `title`, `review_text` | String or null | Review title and body |
| `rating` | Decimal128 or null | Review rating |
| `reviewed_at` | Date or null | UTC review timestamp |
| `helpful_vote` | Int64 or null | Helpful-vote count |
| `verified_purchase` | Boolean or null | Purchase verification flag |

Missing or invalid optional values become null. Valid empty arrays and documents are preserved. Images, videos, product author, subtitle, and bought_together are excluded, matching Phase I.

## Design Decisions and Loading

Product arrays and details are embedded because they describe the same product and can be read together. Reviews are kept separately because a product may have many reviews. Embedding them all could make a product document exceed MongoDB's 16 MiB size limit. Linking reviews through `parent_asin` also avoids copying product information into every review.

The schema file defines field types, required keys, and indexes. The PyMongo loader reuses Phase I cleaning functions, reads the JSONL files in batches of 5,000, and loads products before reviews. Existing IDs are skipped on reruns. Cleanup then checks product references. It checked **43,886,944 reviews**, found **zero unmatched reviews**, and deleted **zero records**.

## Comparison with Phase I MySQL

MySQL uses two tables with `parent_asin` and `(source_id, source_line)` as their primary keys. MongoDB uses two collections with corresponding `_id` keys. Both designs preserve nested product information. MySQL stores it in JSON columns, while MongoDB stores it as BSON arrays and embedded documents. MySQL defines types through table columns, while our MongoDB schema checks document types on future inserts and updates. Cleanup checks cross-collection references at import time.

MongoDB automatically creates unique `_id` indexes. We also created `reviews_parent_asin` on `reviews.parent_asin` to support finding reviews for a product. MySQL uses SQL joins to combine products and reviews. MongoDB can use `$lookup` for this relationship and `$unwind` to process array elements, such as categories. Keeping reviews separate makes these joins necessary when an analysis needs both review measures and product attributes. Equivalent-query performance will be measured in Phase III.
