# Phase II(a) - SQL Queries, Indexes and Timings

## Functional Dependencies

In both tables the primary key decides all the other columns.

| Table | Dependency |
| --- | --- |
| products | parent_asin → title, average_rating, rating_number, price, main_category, store, categories, description, features, details |
| reviews | (source_id, source_line) → parent_asin, user_id, asin, rating, title, review_text, reviewed_at, helpful_vote, verified_purchase |

A review doesn't have its own ID in the data, so we use the file it came from and its line number in that file. We need both because two files can have the same line number.

## Normalization

**1NF** - categories, description, features and details are stored as JSON lists, so they don't fully follow 1NF. We left them like that because we always use them together with the product, and when we need the categories one by one (Q5) we split them with JSON_TABLE.

**2NF** - products has a key with only one column. In reviews, all columns depend on the full key (source_id, source_line), not only on one part of it.

**3NF** - product info is saved only once, in products. Reviews just link to it with parent_asin. So the title, price and store are not copied into every review, and if something changes we only update it in one place.

## Timings Before and After Indexes

| Query | Question | Index | Before | After |
| --- | --- | --- | --- | --- |
| Q1 | How did reviews change over the years? | idx_reviews_time_rating (reviewed_at, rating) | 21.759 s | 17.583 s |
| Q2 | Do more expensive electronics get better ratings? | idx_products_price (price, average_rating, rating_number) | 30.550 s | 0.191 s |
| Q3 | What do the most helpful reviews look like? | idx_reviews_helpful (helpful_vote) | 15.330 s | 0.0145 s |
| Q4 | Do verified buyers rate differently? | idx_reviews_verified (verified_purchase, rating, helpful_vote) | 27.141 s | 20.384 s |
| Q5 | Which sub-categories disappoint buyers the most? | idx_products_rating_number (rating_number, average_rating) | 34.152 s | 32.561 s |

## Index Build Times

| Index | Table | Build time |
| --- | --- | --- |
| idx_reviews_time_rating | reviews | 116.07 s |
| idx_products_price | products | 9.86 s |
| idx_reviews_helpful | reviews | 110.86 s |
| idx_reviews_verified | reviews | 117.88 s |
| idx_products_rating_number | products | 9.90 s |
| Total | | 364.57 s |

The indexes on reviews took much longer to build since reviews has about 44M rows and products only about 1.6M.

## Why the Indexes Helped (or Didn't)

- Q1 - The index has the date and rating, so MySQL doesn't have to read the big review rows. But it still counts every review, so it only got a bit faster.
- Q2 - All three columns the query needs are in the index, so MySQL doesn't open the product rows at all. This is why it went from 30 s to under 1 s.
- Q3 - The index keeps reviews in order of helpful votes. MySQL just takes the top 15 and stops, instead of going through all 44M reviews.
- Q4 - Same as Q1. Everything it needs is in the index, but it still has to count all the reviews.
- Q5 - The index can skip products with less than 10 ratings, but most products have more than that. MySQL still has to open every product to split its category list, so the time barely changed.

## Query Results

Full results for each query are in the [before-index folder](sql_results/before_indexes/) and [after-index folder](sql_results/after_indexes/).

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

Paying more doesn't get you a better rated product. The cheapest group (under $25) has the best average, and $100 - $499 has the most badly rated products.

### Q3 - Most helpful reviews

15 rows in total, these are the top 4.

| Product | Store | Rating | Helpful votes | Verified |
| --- | --- | --- | --- | --- |
| Fire Tablet with Alexa, 7" Display, 16 GB, Blue | Amazon | 5.00 | 46,841 | Yes |
| Fire TV Stick with Alexa Voice Remote | Amazon | 5.00 | 32,948 | Yes |
| Amazon Fire TV - 1st Generation | Amazon | 5.00 | 26,331 | Yes |
| Kindle Wireless Reading Device (6" Display) | Amazon | 1.00 | 24,261 | Yes |

All of the top reviews are on Amazon's own products. The 4th one is a 1-star review warning people about the Kindle, so people find bad reviews just as useful as good ones.

### Q4 - Verified vs. non-verified reviewers

| Reviewer | Reviews | Avg rating | % 5-star | % 1-star | Avg helpful votes |
| --- | --- | --- | --- | --- | --- |
| Verified buyer | 40,546,882 | 4.12 | 64.2 | 11.8 | 0.98 |
| Not verified | 3,340,060 | 3.82 | 53.5 | 16.6 | 2.46 |

We expected non-verified reviewers to give higher ratings, but it's the opposite. They give lower ratings and more 1-stars, and their reviews get about 2.5 times more helpful votes.

### Q5 - Most disappointing sub-categories

15 rows in total, these are the top 5.

| Category | Products | % rated below 3.5 | Avg rating | Avg price |
| --- | --- | --- | --- | --- |
| Hidden Cameras | 1,752 | 50.9 | 3.52 | $71.16 |
| Audio Docks | 1,012 | 46.2 | 3.52 | $101.51 |
| MP3 & MP4 Players | 3,175 | 41.6 | 3.56 | $133.75 |
| DVD Players & Recorders | 1,228 | 39.4 | 3.60 | $181.12 |
| Repeaters | 1,600 | 38.4 | 3.64 | $54.75 |

Hidden cameras are the worst, around half of them are rated below 3.5.