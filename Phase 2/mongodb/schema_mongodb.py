"""Create or update the Phase II MongoDB collection schemas and indexes.

Run before loading a new database, or apply to the already loaded database.
Strict validation checks future inserts and updates, not existing documents.
The parent_asin reference is not a database-enforced foreign key.
"""

import argparse

from pymongo import MongoClient
from pymongo.errors import CollectionInvalid


PRODUCT_SCHEMA = {
    "bsonType": "object",
    "required": ["_id"],
    "properties": {
        "_id": {"bsonType": "string", "minLength": 1},
        "title": {"bsonType": ["string", "null"]},
        "average_rating": {"bsonType": ["decimal", "null"]},
        "rating_number": {"bsonType": ["long", "null"], "minimum": 0},
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
            "additionalProperties": False,
            "properties": {
                "source_id": {"bsonType": "string", "minLength": 1},
                "source_line": {"bsonType": "long", "minimum": 1},
            },
        },
        "parent_asin": {"bsonType": "string", "minLength": 1},
        "user_id": {"bsonType": ["string", "null"]},
        "asin": {"bsonType": ["string", "null"]},
        "rating": {"bsonType": ["decimal", "null"]},
        "title": {"bsonType": ["string", "null"]},
        "review_text": {"bsonType": ["string", "null"]},
        "reviewed_at": {"bsonType": ["date", "null"]},
        "helpful_vote": {"bsonType": ["long", "null"], "minimum": 0},
        "verified_purchase": {"bsonType": ["bool", "null"]},
    },
}


def create_collection(db, name, schema):
    """Create a collection or replace its validation rules on a rerun."""
    options = {
        "validator": {"$jsonSchema": schema},
        "validationLevel": "strict",
        "validationAction": "error",
    }
    try:
        db.create_collection(name, **options)
    except CollectionInvalid:
        db.command({"collMod": name, **options})
    print(f"{name}: schema applied.")


def create_schema(db):
    create_collection(db, "products", PRODUCT_SCHEMA)
    create_collection(db, "reviews", REVIEW_SCHEMA)
    # MongoDB automatically creates the unique _id index on each collection.
    db.reviews.create_index("parent_asin", name="reviews_parent_asin")
    print("Indexes ready.")


def main():
    parser = argparse.ArgumentParser(description="Create the MongoDB schema and indexes.")
    parser.add_argument("--uri", default="mongodb://localhost:27017")
    parser.add_argument("--database", default="amazon_electronics_reviews")
    args = parser.parse_args()

    with MongoClient(args.uri, serverSelectionTimeoutMS=10000) as client:
        client.admin.command("ping")
        create_schema(client[args.database])
    print("Database connection closed.")


if __name__ == "__main__":
    main()
