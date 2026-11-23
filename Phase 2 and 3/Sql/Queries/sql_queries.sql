-- CSCI 620 Project - Phase II(a): SQL queries and indexes

USE amazon_electronics_reviews;

-- Q1: How did reviews change over the years?
SELECT
    YEAR(reviewed_at)                          AS review_year,
    COUNT(*)                                   AS total_reviews,
    ROUND(AVG(rating), 2)                      AS avg_rating,
    ROUND(100 * SUM(rating = 5) / COUNT(*), 1) AS pct_5_star,
    ROUND(100 * SUM(rating = 1) / COUNT(*), 1) AS pct_1_star
FROM reviews
WHERE reviewed_at IS NOT NULL
  AND rating IS NOT NULL
GROUP BY YEAR(reviewed_at)
ORDER BY review_year;

-- Q2: Do more expensive electronics get better ratings?
SELECT
    CASE
        WHEN price < 25  THEN '1. Under $25'
        WHEN price < 100 THEN '2. $25 - $99'
        WHEN price < 500 THEN '3. $100 - $499'
        ELSE                  '4. $500 and up'
    END                                                  AS price_range,
    COUNT(*)                                             AS total_products,
    ROUND(AVG(average_rating), 2)                        AS avg_rating,
    ROUND(100 * SUM(average_rating < 3.5) / COUNT(*), 1) AS pct_low_rated,
    ROUND(AVG(rating_number))                            AS avg_ratings_per_product
FROM products
WHERE price IS NOT NULL
  AND average_rating IS NOT NULL
  AND rating_number >= 10
GROUP BY price_range
ORDER BY price_range;

-- Q3: What do the most helpful reviews look like?
SELECT
    LEFT(p.title, 50) AS product,
    p.store,
    r.rating,
    r.helpful_vote,
    r.verified_purchase,
    LEFT(r.title, 60) AS review_title
FROM reviews r
JOIN products p ON p.parent_asin = r.parent_asin
WHERE r.helpful_vote >= 1000
ORDER BY r.helpful_vote DESC
LIMIT 15;

-- Q4: Do verified buyers rate differently from non-verified reviewers?
SELECT
    CASE WHEN verified_purchase THEN 'Verified buyer' ELSE 'Not verified' END AS reviewer,
    COUNT(*)                                   AS total_reviews,
    ROUND(AVG(rating), 2)                      AS avg_rating,
    ROUND(100 * SUM(rating = 5) / COUNT(*), 1) AS pct_5_star,
    ROUND(100 * SUM(rating = 1) / COUNT(*), 1) AS pct_1_star,
    ROUND(AVG(helpful_vote), 2)                AS avg_helpful_votes
FROM reviews
WHERE verified_purchase IS NOT NULL
  AND rating IS NOT NULL
GROUP BY verified_purchase
ORDER BY verified_purchase DESC;

-- Q5: Which sub-categories disappoint buyers the most?
SELECT
    c.category,
    COUNT(*)                                               AS total_products,
    ROUND(100 * SUM(p.average_rating < 3.5) / COUNT(*), 1) AS pct_low_rated,
    ROUND(AVG(p.average_rating), 2)                        AS avg_rating,
    ROUND(AVG(p.price), 2)                                 AS avg_price
FROM products p,
     JSON_TABLE(
         p.categories,
         '$[*]' COLUMNS (category VARCHAR(255) PATH '$')
     ) AS c
WHERE c.category <> 'Electronics'
  AND p.average_rating IS NOT NULL
  AND p.rating_number >= 10
GROUP BY c.category
HAVING COUNT(*) >= 1000
ORDER BY pct_low_rated DESC
LIMIT 15;

-- Indexes
CREATE INDEX idx_reviews_time_rating    ON reviews  (reviewed_at, rating);
CREATE INDEX idx_products_price         ON products (price, average_rating, rating_number);
CREATE INDEX idx_reviews_helpful        ON reviews  (helpful_vote);
CREATE INDEX idx_reviews_verified       ON reviews  (verified_purchase, rating, helpful_vote);
CREATE INDEX idx_products_rating_number ON products (rating_number, average_rating);