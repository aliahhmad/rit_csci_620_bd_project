# Phase II(b) — MongoDB Design and Comparison with MySQL

We used MongoDB to store the Electronics subset of Amazon Reviews 2023. The database, `amazon_electronics_reviews`, contains **1,610,012 products** and **43,886,944 reviews**. We checked these totals using mongosh.

We created two collections, `products` and `reviews`. Each document in `products` stores one product. Its `_id` is the product's `parent_asin`. The other fields are `title`, `average_rating`, `rating_number`, `price`, `main_category`, and `store`. Categories, descriptions, and features are stored as arrays inside the product document. The `details` field stores an embedded document with attributes such as the manufacturer and color.

Each document in `reviews` stores one review. Its `_id` contains `source_id` and `source_line`, which together identify the original record in the dataset. The remaining fields are `parent_asin`, `user_id`, `asin`, `rating`, `title`, `review_text`, `reviewed_at`, `helpful_vote`, and `verified_purchase`. Text fields use strings, ratings and prices use Decimal128, counts and source line numbers use 64-bit integers, timestamps use UTC dates, and purchase verification uses a boolean. Missing or invalid optional values become null.

We kept product information together because it describes the same product. Reviews are stored separately because a product may have many reviews. Putting every review inside its product document could make that document too large. Each review links to a product through `parent_asin`, so product information does not need to be copied into every review.

The `schema_mongodb.py` file defines the field types, required keys, and indexes. The `load_mongodb.py` file reads the JSONL files in batches of 5,000 and uses the Phase I cleaning functions from `util.py`. It loads products first, then reviews, and finally checks whether each review has a matching product. Cleanup checked all **43,886,944 reviews**, found **no unmatched reviews**, and deleted **no records**. Existing document IDs are skipped when the loader runs again.

MySQL stores this data in tables, while MongoDB stores it in documents. Both designs keep products and reviews separate and use the same identifiers. Both also store nested product information. MySQL uses JSON columns for this information, while MongoDB uses arrays and embedded documents. Queries can combine products and reviews using SQL joins in MySQL or `$lookup` in MongoDB. MongoDB can also use `$unwind` to process categories individually.

MongoDB automatically creates a unique `_id` index for each collection. We also created an index on `reviews.parent_asin` to help find reviews for a product. MySQL defines field types through its table schema. Our MongoDB schema checks field types when documents are inserted or updated, while cleanup checks that product references exist. Query performance will be measured in Phase III.
