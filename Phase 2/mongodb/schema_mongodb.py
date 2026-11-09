"""
MongoDB document model for Amazon Electronics.
products._id stores parent_asin, the product primary key.
reviews._id combines source_id and source_line, the review primary key.
reviews.parent_asin references products._id without a foreign key constraint.
Metadata arrays and product details are embedded in each product document.
"""

import argparse

from pymongo import MongoClient


# Nullable fields correspond to nullable columns in the MySQL schema.
PRODUCT_SCHEMA = {
    "bsonType": "object",
    "required": ["_id"],
    "properties": {
        "_id": {"bsonType": "string"},  # parent_asin
        "title": {"bsonType": ["string", "null"]},
        "average_rating": {"bsonType": ["decimal", "null"]},
        "rating_number": {"bsonType": ["long", "null"]},
        "price": {"bsonType": ["decimal", "null"]},
        "main_category": {"bsonType": ["string", "null"]},
        "store": {"bsonType": ["string", "null"]},
        "categories": {"bsonType": ["array", "null"]},
        "description": {"bsonType": ["array", "null"]},
        "features": {"bsonType": ["array", "null"]},
        "details": {"bsonType": ["object", "null"]},
    },
}

REVIEW_SCHEMA = {
    "bsonType": "object",
    "required": ["_id", "parent_asin"],
    "properties": {
        "_id": {
            "bsonType": "object",
            "required": ["source_id", "source_line"],
            "properties": {
                "source_id": {"bsonType": "string"},
                "source_line": {"bsonType": "long"},
            },
        },
        "parent_asin": {"bsonType": "string"},
        "user_id": {"bsonType": ["string", "null"]},
        "asin": {"bsonType": ["string", "null"]},
        "rating": {"bsonType": ["decimal", "null"]},
        "title": {"bsonType": ["string", "null"]},
        "review_text": {"bsonType": ["string", "null"]},
        "reviewed_at": {"bsonType": ["date", "null"]},
        "helpful_vote": {"bsonType": ["long", "null"]},
        "verified_purchase": {"bsonType": ["bool", "null"]},
    },
}


def create_schema(db):
    """Declare collections and field types, including on an existing database."""
    existing = db.list_collection_names()
    for name, schema in (("products", PRODUCT_SCHEMA), ("reviews", REVIEW_SCHEMA)):
        options = {
            "validator": {"$jsonSchema": schema},
            "validationLevel": "strict",
            "validationAction": "error",
        }
        if name in existing:
            db.command({"collMod": name, **options})
        else:
            db.create_collection(name, **options)
        print(f"{name}: schema applied.")

    # MongoDB automatically creates the unique _id indexes.
    db.reviews.create_index("parent_asin", name="reviews_parent_asin")
    print("Indexes ready.")


def main():
    parser = argparse.ArgumentParser(description="Create MongoDB collections and indexes.")
    parser.add_argument("--uri", default="mongodb://localhost:27017")
    parser.add_argument("--database", default="amazon_electronics_reviews")
    args = parser.parse_args()

    with MongoClient(args.uri, serverSelectionTimeoutMS=10000) as client:
        client.admin.command("ping")
        create_schema(client[args.database])
    print("Database connection closed.")


if __name__ == "__main__":
    main()
