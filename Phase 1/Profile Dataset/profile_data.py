import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

REVIEWS_FILE = Path("Amazon Electronics Dataset/Electronics.jsonl")
METADATA_FILE = Path("Amazon Electronics Dataset/meta_Electronics.jsonl")
PROFILE_LIMIT = 100000


def read_json(path):
    """Read one record at a time; return None for invalid records."""
    path = Path(path)

    with path.open("r", encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue

            try:
                row = json.loads(line, parse_constant=lambda x: None)

                if isinstance(row, dict):
                    yield line_no, row
                else:
                    yield line_no, None

            except ValueError:
                yield line_no, None


def profile(path, label):
    """Profile the top level fields in a JSON file without loading the entire file into memory."""
    counts = defaultdict(Counter)
    types = defaultdict(Counter)
    scanned = valid = invalid = 0

    for _, obj in read_json(path):
        scanned += 1

        if obj is None:
            invalid += 1
        else:
            valid += 1

            for field, value in obj.items():
                counts[field]["present"] += 1
                types[field][type(value).__name__] += 1

                if value is None:
                    counts[field]["null"] += 1
                elif isinstance(value, str) and not value.strip():
                    counts[field]["blank_string"] += 1
                elif isinstance(value, (dict, list)) and not value:
                    counts[field]["empty_container"] += 1

        if PROFILE_LIMIT is not None and scanned >= PROFILE_LIMIT:
            break

    folder = Path("reports")
    folder.mkdir(exist_ok=True)
    output = folder / f"{label}_fields_phase_1.csv"

    with output.open("w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)

        writer.writerow(
            [
                "field",
                "types",
                "absent",
                "null",
                "blank_string",
                "empty_container",
                "missing_percent",
            ]
        )

        for field in sorted(counts):
            c = counts[field]
            absent = valid - c["present"]
            missing = absent + c["null"] + c["blank_string"]
            pct = round(100 * missing / valid, 3) if valid else 0

            writer.writerow(
                [
                    field,
                    dict(types[field]),
                    absent,
                    c["null"],
                    c["blank_string"],
                    c["empty_container"],
                    pct,
                ]
            )


if __name__ == "__main__":
    profile(REVIEWS_FILE, "reviews")
    profile(METADATA_FILE, "metadata")
