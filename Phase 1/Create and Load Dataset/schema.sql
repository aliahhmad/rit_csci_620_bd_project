CREATE DATABASE IF NOT EXISTS amazon_electronics_reviews;

USE amazon_electronics_reviews;

CREATE TABLE IF NOT EXISTS products (
    parent_asin VARCHAR(20) PRIMARY KEY,
    title LONGTEXT,
    average_rating DECIMAL(3, 2),
    rating_number BIGINT,
    price DECIMAL(15, 2),
    main_category TEXT,
    store TEXT,
    categories JSON,
    description JSON,
    features JSON,
    details JSON
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS reviews (
    source_id VARCHAR(100) NOT NULL,
    source_line BIGINT NOT NULL,
    parent_asin VARCHAR(20) NOT NULL,
    user_id VARCHAR(100),
    asin VARCHAR(20),
    rating DECIMAL(3, 2),
    title LONGTEXT,
    review_text LONGTEXT,
    reviewed_at DATETIME(3),
    helpful_vote BIGINT,
    verified_purchase BOOLEAN,

    PRIMARY KEY (source_id, source_line)
) ENGINE = InnoDB;