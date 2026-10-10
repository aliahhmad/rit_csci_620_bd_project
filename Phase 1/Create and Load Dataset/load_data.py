import mysql.connector
from util import read_json, text, number, boolean, review_time, json_value

BATCH_SIZE = 5000
SOURCE_ID = "amazon2023-electronics"


def load_products(conn, cursor):
    """Load product metadata into the products table."""
    print("Loading Products...")

    sql = """
        INSERT INTO products
        (parent_asin, title, average_rating, rating_number, price,
         main_category, store, categories, description, features, details)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE parent_asin = products.parent_asin
    """

    batch = []

    for _, row in read_json("meta_Electronics.jsonl"):
        if row is None:
            continue

        parent = text(row.get("parent_asin"))
        if parent is None:
            continue

        batch.append(
            (
                parent,
                text(row.get("title")),
                number(row.get("average_rating"), rating=True),
                number(row.get("rating_number"), integer=True),
                number(row.get("price")),
                text(row.get("main_category")),
                text(row.get("store")),
                json_value(row.get("categories"), list),
                json_value(row.get("description"), list),
                json_value(row.get("features"), list),
                json_value(row.get("details"), dict),
            )
        )

        if len(batch) >= BATCH_SIZE:
            cursor.executemany(sql, batch)
            conn.commit()
            batch.clear()

    if batch:
        cursor.executemany(sql, batch)
        conn.commit()

    print("Products finished.")


def load_reviews(conn, cursor):
    """Load reviews into the reviews table."""
    print("Loading Reviews...")

    sql = """
        INSERT INTO reviews
        (source_id, source_line, parent_asin, user_id, asin, rating,
         title, review_text, reviewed_at, helpful_vote, verified_purchase)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE source_line = reviews.source_line
    """

    batch = []

    for line_no, row in read_json("Electronics.jsonl"):
        if row is None:
            continue

        parent = text(row.get("parent_asin"))
        if parent is None:
            continue

        reviewed_at = review_time(row.get("timestamp"))
        if reviewed_at is not None:
            if reviewed_at.year < 1000:
                reviewed_at = None
            else:
                reviewed_at = reviewed_at.replace(tzinfo=None)

        batch.append(
            (
                SOURCE_ID,
                line_no,
                parent,
                text(row.get("user_id")),
                text(row.get("asin")),
                number(row.get("rating"), rating=True),
                text(row.get("title")),
                text(row.get("text")),
                reviewed_at,
                number(row.get("helpful_vote"), integer=True),
                boolean(row.get("verified_purchase")),
            )
        )

        if len(batch) >= BATCH_SIZE:
            cursor.executemany(sql, batch)
            conn.commit()
            batch.clear()

    if batch:
        cursor.executemany(sql, batch)
        conn.commit()

    print("Reviews finished.")


def cleanup_reviews(conn, cursor):
    """Delete reviews that don't match any product."""
    print("Cleaning Reviews...", flush=True)

    last_line = 0

    while True:
        cursor.execute(
            """
            SELECT source_line
            FROM reviews
            WHERE source_id = %s AND source_line > %s
            ORDER BY source_line
            LIMIT 5000
        """,
            (SOURCE_ID, last_line),
        )

        rows = cursor.fetchall()

        if not rows:
            break

        end_line = rows[-1][0]

        # Delete reviews that don't match any product in the current batch
        cursor.execute(
            """
            DELETE FROM reviews
            WHERE source_id = %s
              AND source_line > %s
              AND source_line <= %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM products
                  WHERE products.parent_asin = reviews.parent_asin
              )
        """,
            (SOURCE_ID, last_line, end_line),
        )

        conn.commit()
        last_line = end_line

        print(f"Cleaned through source line {last_line:,}", flush=True)

    # Add foreign key constraint to ensure relationship between reviews and products
    cursor.execute("""
        ALTER TABLE reviews
        ADD CONSTRAINT reviews_product_fk
        FOREIGN KEY (parent_asin)
        REFERENCES products(parent_asin)
    """)

    print("Cleanup finished.")


def main():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="amazon_electronics_reviews",
    )

    cursor = conn.cursor()

    try:
        load_products(conn, cursor)
        load_reviews(conn, cursor)
        cleanup_reviews(conn, cursor)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
        print("Database connection closed.")


if __name__ == "__main__":
    main()
