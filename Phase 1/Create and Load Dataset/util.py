import json
import math
from pathlib import Path
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone


DATA_FOLDER = "Amazon Electronics Dataset"


def read_json(filename):
    """Read one record at a time without loading the whole file."""
    path = Path(DATA_FOLDER) / filename

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


def text(value):
    """Return text, or None for missing, blank, or invalid values."""
    if not isinstance(value, str):
        return None

    value = value.replace("\x00", "")
    value = value.encode("utf-8", "replace").decode("utf-8")

    if not value.strip():
        return None

    return value


def number(value, integer=False, rating=False):
    """Validate numbers for the BIGINT and DECIMAL schema columns."""
    if value is None or isinstance(value, bool):
        return None

    try:
        result = Decimal(str(value))

        if not result.is_finite() or result < 0:
            return None

        if rating:
            if not 1 <= result <= 5:
                return None

        if integer:
            if result != result.to_integral_value():
                return None

            if result > 9223372036854775807:
                return None

            return int(result)

        # Non rating decimal values are prices: DECIMAL(15, 2).
        if not rating and result > Decimal("9999999999999.99"):
            return None

        return result

    except (InvalidOperation, ValueError, TypeError):
        return None


def boolean(value):
    """Keep actual True/False values; anything else becomes NULL."""
    if type(value) is bool:
        return value

    return None


def review_time(value):
    """Convert Unix milliseconds into a UTC datetime."""
    milliseconds = number(value, integer=True)

    if milliseconds is None:
        return None

    try:
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        return epoch + timedelta(milliseconds=milliseconds)

    except (OverflowError, ValueError):
        return None


def clean_nested(value):
    """Clean unsupported characters and nonfinite numbers in JSON."""
    if isinstance(value, str):
        value = value.replace("\x00", "")
        return value.encode("utf-8", "replace").decode("utf-8")

    if isinstance(value, list):
        return [clean_nested(item) for item in value]

    if isinstance(value, dict):
        return {
            clean_nested(key): clean_nested(item)
            for key, item in value.items()
        }

    if isinstance(value, float) and not math.isfinite(value):
        return None

    return value


def json_value(value, expected_type):
    """Convert a list or dictionary to JSON text for MySQL."""
    if not isinstance(value, expected_type):
        return None

    return json.dumps(clean_nested(value), allow_nan=False)