# Phase III(a) - MongoDB Aggregation Queries, Indexes and Timings

We created two collections in MongoDB containing the 2023 Electronic Amazon Reviews dataset. This gave us **1610012 products** and **43886944 reviews**.

| Query | What it does | Pipeline stages |
| --- | --- | --- |
| Q1 - Reviews per year | Takes reviews that have a date and a rating, then for each year (UTC) counts them, gets the average rating and the share of 5-star and 1-star reviews. | $match → $group → $project → $sort |
| Q2 - Price vs. rating | Takes products with a price, a rating and at least 10 ratings, and puts them into 4 price ranges using $switch. | $match → $group → $project → $sort |
| Q3 - Helpful reviews | Takes reviews with at least 1,000 helpful votes, joins reviews.parent_asin to products._id, and returns the top 15. | $match → $sort → $lookup → $unwind → $limit → $project |
| Q4 - Verified reviewers | Takes reviews with a known verified status and rating, and compares counts, ratings, star shares and helpful votes. | $match → $group → $sort → $project |
| Q5 - Disappointing categories | Takes products with a rating and at least 10 ratings, splits the categories list, drops "Electronics" and empty ones, keeps categories with at least 1,000 products and returns the top 15 by share of low ratings. | $match → $unwind → $match → $group → $match → $project → $sort → $limit |

We represented each product by one document in the `products` collection. The field named `_id` contains the clean `parent_asin` value from the original data.

## Timings Before and After Indexes

Each query was run once before and once after adding the five indexes. The time is measured from calling aggregate() until toArray() finishes, and doesn't include saving the results to a file. It is not the executionTimeMillis from explain. All pipelines run with allowDiskUse: true.

Also, the review from the source is represented by one document in the `reviews` collection. Equivalent to the primary keys we have in MySQL, in MongoDB we have `_id` field with an embedded document where `source_id` and `source_line` are combined.

| Query | Question | Index | Before | After |
| --- | --- | --- | --- | --- |
| Q1 | How did reviews change over the years? | idx_reviews_time_rating (reviewed_at, rating) | 81.753 s | 18.686 s |
| Q2 | Do more expensive electronics get better ratings? | idx_products_price (price, average_rating, rating_number) | 7.227 s | 0.417 s |
| Q3 | What do the most helpful reviews look like? | idx_reviews_helpful (helpful_vote) | 60.759 s | 0.0230 s |
| Q4 | Do verified buyers rate differently? | idx_reviews_verified (verified_purchase, rating, helpful_vote) | 84.247 s | 28.682 s |
| Q5 | Which sub-categories disappoint buyers the most? | idx_products_rating_number (rating_number, average_rating) | 7.807 s | 11.495 s |

## Index Build Times

| Index | Collection | Build time |
| --- | --- | --- |
| idx_reviews_time_rating | reviews | 92.30 s |
| idx_products_price | products | 7.05 s |
| idx_reviews_helpful | reviews | 80.46 s |
| idx_reviews_verified | reviews | 91.03 s |
| idx_products_rating_number | products | 7.14 s |
| Total | | 277.98 s |

## Why the Indexes Helped (or Didn't)

- Q1 - The index has the date and rating, so MongoDB doesn't have to read the full review documents as much. It still has to go through almost every review to count them by year.
- Q2 - All three fields the pipeline uses are in the index, so MongoDB can avoid reading the big product documents with descriptions and other long fields.
- Q3 - The index keeps reviews in order of helpful votes, so MongoDB finds the ones over 1,000 and takes the highest right away. The _id_ index on products makes the $lookup fast, and only 15 reviews get joined.
- Q4 - The index has the verified status, rating and helpful votes, so fewer full documents are read. But it still has to count and average almost all the reviews.
- Q5 - The index helps with the rating count filter, but MongoDB still has to $unwind every product's categories, group them and sort the percentages. This query actually got slower with the index.

## Query Results

Full results for each query are in the [before-index folder](mongodb_results/before_indexes/) and [after-index folder](mongodb_results/after_indexes/).

### Q1 - Reviews per year

27 rows in total, these are the first years.

| Year | Reviews | Avg rating | % 5-star | % 1-star |
| --- | --- | --- | --- | --- |
| 1996 | 1 | 4.00 | 0.0 | 0.0 |
| 1998 | 9 | 4.78 | 77.8 | 0.0 |
| 1999 | 419 | 4.15 | 55.4 | 6.7 |
| 2000 | 3,756 | 4.14 | 53.9 | 7.4 |
| 2001 | 6,841 | 3.97 | 49.7 | 10.5 |

The rest of the years are in Q1_result.csv.

### Q2 - Price range vs. rating

Only products with 10 or more ratings.

| Price range | Products | Avg rating | % rated below 3.5 | Avg ratings per product |
| --- | --- | --- | --- | --- |
| Under $25 | 182,113 | 4.27 | 4.5 | 519 |
| $25 - $99 | 97,703 | 4.19 | 6.7 | 566 |
| $100 - $499 | 45,074 | 4.16 | 7.4 | 410 |
| $500 and up | 10,682 | 4.20 | 6.1 | 167 |

Paying more doesn't get you a better rated product. The cheapest group (under $25) has the best average and the fewest badly rated products, and $100 - $499 has the most.

### Q3 - Most helpful reviews

15 rows in total, these are the top 4.

| Product | Store | Rating | Helpful votes | Verified |
| --- | --- | --- | --- | --- |
| Fire Tablet with Alexa, 7" Display, 16 GB, Blue | Amazon | 5.00 | 46,841 | Yes |
| Fire TV Stick with Alexa Voice Remote | Amazon | 5.00 | 32,948 | Yes |
| Amazon Fire TV - 1st Generation | Amazon | 5.00 | 26,331 | Yes |
| Kindle Wireless Reading Device (6" Display) | Amazon | 1.00 | 24,261 | Yes |

All of the top reviews are on Amazon's own products. The 4th one is a 1-star review warning people about the Kindle, so people find bad reviews just as useful as good ones.

If optional fields are missing or invalid, it produces null values. If the array of document is valid and empty, it is left as null. The fields like images, videos, author, subtitle and bought_together are not included as in phase I.

| Reviewer | Reviews | Avg rating | % 5-star | % 1-star | Avg helpful votes |
| --- | --- | --- | --- | --- | --- |
| Verified buyer | 40,546,882 | 4.12 | 64.2 | 11.8 | 0.98 |
| Not verified | 3,340,060 | 3.82 | 53.5 | 16.6 | 2.46 |

We embedded arrays and details within the product collection as they describe the same product. There can be many reviews per product, so we kept reviews separately. Document size can exceed the 16MiB limit if all reviews are nested within product documents. So by having separate reviews, and referencing products via `parent_asin`, we avoid duplicating information.

The schema specifies the data type of each field, primary keys, and indexes. Using PyMongo, the data was loaded by applying the same cleaning methods as phase I. Reviews were batched in 5000 lines, and products were loaded before reviews. Duplicate entries from reruns were skipped. Clean-up was performed. This checked foreign keys in products. 43886944 reviews were checked. 0 had un-matched foreign keys. 0 entries were removed.
The data type of each field, primary keys, and indexes are specified by the schema. The cleaning functions from phase I are used by PyMango loader to read the JSONL files in batches of 5000 and loads products before reviews. We skip duplicate entries from reruns. After loading, we perform clean-up to check product references. We checked 43886944 reviews. 0 had un-matched foreign keys. 0 entries were removed.

15 rows in total, these are the top 5.

In MySQL, we used two tables. The product key is `parent_asin`, and the review key combines `source_id` and `source_line`. In MongoDB, we used the same keys in the `_id` fields of the two collections. We kept the nested product information in JSON columns in MySQL and in BSON arrays and embedded documents in MongoDB. MySQL defines data types in the table columns, and our MongoDB schema checks field types when documents are inserted or updated. After loading the data, we check the product references during cleanup.

MongoDB automatically creates a unique index on `_id` in each collection. We also added the `reviews_parent_asin` index on `reviews.parent_asin` so we can quickly find reviews for a product. When a query needs both review data and product details, we can join them in MySQL with a SQL join and in MongoDB with `$lookup`. We can also use `$unwind` in MongoDB to work with each category in a product's category array. In Phase III, we will compare how long the equivalent queries take in both databases.
