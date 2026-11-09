import argparse
from collections import Counter
from decimal import ROUND_HALF_UP, localcontext
from pathlib import Path

from bson import BSON, Decimal128, Int64
from bson.errors import InvalidDocument
from pymongo import MongoClient
from pymongo.errors import BulkWriteError

import util
from util import read_json, text, number, boolean, review_time, clean_nested

BATCH_SIZE = 5000
SOURCE_ID = "amazon2023-electronics"


def decimal_value(value, rating=False):
    """Use the Phase I number rules and MySQL's two decimal places."""
    value = number(value, rating=rating)
    if value is None:
        return None
    with localcontext() as context:
        context.prec = max(34, len(value.as_tuple().digits) + 4)
        return Decimal128(value.quantize(number("0.01"), rounding=ROUND_HALF_UP))


def integer_value(value):
    value = number(value, integer=True)
    return None if value is None else Int64(value)


def nested_value(value, expected_type):
    if not isinstance(value, expected_type):
        return None
    return clean_nested(value)


def product_document(row, parent):
    return {
        "_id": parent,
        "title": text(row.get("title")),
        "average_rating": decimal_value(row.get("average_rating"), rating=True),
        "rating_number": integer_value(row.get("rating_number")),
        "price": decimal_value(row.get("price")),
        "main_category": text(row.get("main_category")),
        "store": text(row.get("store")),
        "categories": nested_value(row.get("categories"), list),
        "description": nested_value(row.get("description"), list),
        "features": nested_value(row.get("features"), list),
        "details": nested_value(row.get("details"), dict),
    }


def review_document(row, parent, line_no):
    reviewed_at = review_time(row.get("timestamp"))
    return {
        "_id": {"source_id": SOURCE_ID, "source_line": Int64(line_no)},
        "parent_asin": parent,
        "user_id": text(row.get("user_id")),
        "asin": text(row.get("asin")),
        "rating": decimal_value(row.get("rating"), rating=True),
        "title": text(row.get("title")),
        "review_text": text(row.get("text")),
        "reviewed_at": reviewed_at,
        "helpful_vote": integer_value(row.get("helpful_vote")),
        "verified_purchase": boolean(row.get("verified_purchase")),
    }


def write_batch(db, collection, batch, stats, require_product):
    """Insert in source order, keeping the first occurrence of each key."""
    if require_product:
        parents = list({document["parent_asin"] for document in batch})
        matches = {row["_id"] for row in db.products.find(
            {"_id": {"$in": parents}}, {"_id": 1}
        )}
        retained = [document for document in batch if document["parent_asin"] in matches]
        stats["unmatched_product"] += len(batch) - len(retained)
        batch = retained

    # Deduplicate this batch before unordered writes so first metadata wins.
    unique = {}
    for document in batch:
        key = BSON.encode({"_id": document["_id"]})
        if key in unique:
            stats["duplicate"] += 1
        else:
            unique[key] = document
    if not unique:
        return
    try:
        result = db[collection].insert_many(list(unique.values()), ordered=False)
        stats["inserted"] += len(result.inserted_ids)
    except BulkWriteError as error:
        stats["inserted"] += error.details.get("nInserted", 0)
        failures = error.details.get("writeErrors", [])
        stats["duplicate"] += sum(item["code"] == 11000 for item in failures)
        if error.details.get("writeConcernErrors") or any(
            item["code"] != 11000 for item in failures
        ):
            raise


def load_collection(db, filename, collection, limit=None, require_product=False):
    print(f"Loading {collection}...", flush=True)
    stats = Counter(inserted=0, duplicate=0, missing_parent=0,
                    invalid=0, unmatched_product=0, scanned=0)
    batch = []
    for line_no, row in read_json(filename):
        if limit is not None and line_no > limit:
            break
        stats["scanned"] += 1
        if row is None:
            stats["invalid"] += 1
            continue
        parent = text(row.get("parent_asin"))
        if parent is None:
            stats["missing_parent"] += 1
            continue
        if collection == "products":
            document = product_document(row, parent)
        else:
            document = review_document(row, parent, line_no)
        try:
            encoded = BSON.encode(document)
        except (InvalidDocument, OverflowError) as error:
            raise ValueError(f"{filename}, line {line_no}: unsupported BSON value") from error
        if len(encoded) > 16 * 1024 * 1024:
            raise ValueError(f"{filename}, line {line_no}: exceeds BSON document size limit")
        batch.append(document)
        if len(batch) >= BATCH_SIZE:
            write_batch(db, collection, batch, stats, require_product)
            batch.clear()
            print(f"{collection}: through source line {line_no:,}", flush=True)
    if batch:
        write_batch(db, collection, batch, stats, require_product)
    print(f"{collection} finished: {dict(stats)}", flush=True)
    return stats



def cleanup_reviews(db, count_only=False, limit=None):
    """Check reviews in source order and remove those without product metadata.

    Run after products finish loading. Keep products and reviews unchanged by
    other processes during cleanup. Restarting safely rechecks surviving rows.
    """
    existing = db.list_collection_names()
    if "products" not in existing or "reviews" not in existing:
        raise ValueError("Both products and reviews must exist before cleanup.")
    if db.products.find_one({}, {"_id": 1}) is None:
        raise ValueError("Products is empty. Complete metadata loading before cleanup.")

    print("Checking reviews for matching products...", flush=True)
    scanned = unmatched = deleted = 0
    last_id = {"source_id": SOURCE_ID, "source_line": Int64(0)}
    end_id = {"source_id": SOURCE_ID,
              "source_line": Int64(limit if limit is not None else 9223372036854775807)}

    while True:
        batch = list(db.reviews.find(
            {"_id": {"$gt": last_id, "$lte": end_id}},
            {"_id": 1, "parent_asin": 1},
        ).sort("_id", 1).limit(BATCH_SIZE))
        if not batch:
            break

        parents = list({row["parent_asin"] for row in batch})
        matches = {row["_id"] for row in db.products.find(
            {"_id": {"$in": parents}}, {"_id": 1}
        )}
        missing_ids = [row["_id"] for row in batch if row["parent_asin"] not in matches]
        scanned += len(batch)
        unmatched += len(missing_ids)
        if missing_ids and not count_only:
            result = db.reviews.delete_many({"_id": {"$in": missing_ids}})
            deleted += result.deleted_count

        last_id = batch[-1]["_id"]
        print(f"Cleanup: checked {scanned:,}, unmatched {unmatched:,}, "
              f"deleted {deleted:,}", flush=True)

    stats = {"checked": scanned, "unmatched": unmatched, "deleted": deleted}
    print(f"Cleanup finished: {stats}", flush=True)
    return stats


def main():
    parser = argparse.ArgumentParser(description="Load Amazon Electronics JSONL into MongoDB.")
    parser.add_argument("--uri", default="mongodb://localhost:27017")
    parser.add_argument("--database", default="amazon_electronics_reviews")
    parser.add_argument("--data-folder", default=util.DATA_FOLDER)
    parser.add_argument("--limit", type=int, help="Read up to this physical line in each file.")
    parser.add_argument("--require-product", action="store_true",
                        help="Skip reviews without matching metadata; use a fresh database.")
    parser.add_argument("--cleanup-only", action="store_true",
                        help="Clean existing reviews without reading JSONL files.")
    parser.add_argument("--count-only", action="store_true",
                        help="With --cleanup-only, count unmatched reviews without deleting.")
    args = parser.parse_args()
    if args.count_only and not args.cleanup_only:
        parser.error("--count-only requires --cleanup-only")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    util.DATA_FOLDER = Path(args.data_folder)
    with MongoClient(args.uri, serverSelectionTimeoutMS=10000, tz_aware=True) as client:
        client.admin.command("ping")
        db = client[args.database]
        if not args.cleanup_only:
            load_collection(db, "meta_Electronics.jsonl", "products", args.limit)
            load_collection(db, "Electronics.jsonl", "reviews", args.limit, args.require_product)
        cleanup_reviews(db, count_only=args.count_only, limit=args.limit)
        db.reviews.create_index("parent_asin", name="reviews_parent_asin")
    print("Database connection closed.")


if __name__ == "__main__":
    main()
