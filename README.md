# Amazon Electronics Reviews: Relational and Document Database Analysis

**CSCI-620 | Introduction to Big Data**

## Project Description

Amazon product reviews combine customer feedback with product metadata, including ratings, prices, categories, and purchase verification. Analyzing this data at scale requires a database model that preserves useful relationships while handling missing values, inconsistent types, and nested attributes.

This project uses the Electronics category of Amazon Reviews 2023 to explore relational and document-oriented data management. Phase 1 profiles the source files, defines a MySQL schema, and provides utilities for validating and loading records. Later phases will introduce SQL workloads, indexing, a MongoDB model, and performance comparisons between the two database systems.

## Phase 1 — Dataset Profiling & Relational Data Loading

### Dataset

The dataset comes from McAuley Lab's **Amazon Reviews 2023** collection. The published Electronics statistics list approximately **43.9 million reviews** and **1.6 million items represented in reviews**; these are source statistics, not verified database row counts. Some reviewed items lack product metadata. [Dataset source and statistics](https://amazon-reviews-2023.github.io/).

Two JSON Lines files are used, each containing one JSON object per line:

- `Electronics.jsonl` — Customer reviews, including ratings, review titles and text, product identifiers, user identifiers, timestamps, helpful votes, and verified-purchase status.
- `meta_Electronics.jsonl` — Product metadata, including titles, average ratings, rating counts, prices, stores, categories, descriptions, features, and details.

Download the files from the links recorded in the Phase 1 report:

- [Electronics reviews](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/raw/review_categories/Electronics.jsonl?download=true)
- [Electronics product metadata](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/raw/meta_categories/meta_Electronics.jsonl?download=true)

Place both files in `Amazon Electronics Dataset/` at the project root. The raw JSONL files are excluded from version control through `.gitignore`.

### Dataset Profiling

[profile_data.py](Phase%201/Profile%20Dataset/profile_data.py) streams each file and profiles its first **100,000 nonblank records**. It records the following for every observed top-level field:

- Observed Python types and their counts.
- Absent fields, explicit nulls, and blank strings.
- Empty lists and dictionaries.
- Missing percentage, calculated from absent fields, nulls, and blank strings among valid records.

Empty containers are reported separately and do not contribute to the missing percentage. Set `PROFILE_LIMIT = None` to scan the full files.

### Phase 1 Profiling Results

View the complete reports:

- [Metadata field profile](Reports/metadata_fields_phase_1.csv)
- [Review field profile](Reports/reviews_fields_phase_1.csv)
- [Phase 1 report](Reports/CSCI%20620_%20Project%20Phase%201.pdf)

### Relational Model

[schema.sql](Phase%201/Create%20and%20Load%20Dataset/schema.sql) creates the `amazon_electronics_reviews` database with two InnoDB tables.

**Products**

| Column | MySQL type | Purpose |
| --- | --- | --- |
| `parent_asin` | `VARCHAR(20)` primary key | Product identifier shared with reviews |
| `title` | `LONGTEXT` | Product title |
| `average_rating` | `DECIMAL(3, 2)` | Average product rating |
| `rating_number` | `BIGINT` | Number of ratings |
| `price` | `DECIMAL(15, 2)` | Product price |
| `main_category`, `store` | `TEXT` | Category and store information |
| `categories`, `description`, `features` | `JSON` | Nested lists preserved from metadata |
| `details` | `JSON` | Product attributes preserved as an object |

**Reviews**

| Column | MySQL type | Purpose |
| --- | --- | --- |
| `source_id` | `VARCHAR(100)` | Dataset identifier |
| `source_line` | `BIGINT` | Original JSONL line number |
| `parent_asin` | `VARCHAR(20) NOT NULL` | Link to the product |
| `user_id` | `VARCHAR(100)` | Reviewer identifier |
| `asin` | `VARCHAR(20)` | Reviewed item or variant identifier |
| `rating` | `DECIMAL(3, 2)` | Review rating |
| `title`, `review_text` | `LONGTEXT` | Review title and body |
| `reviewed_at` | `DATETIME(3)` | Review timestamp stored in UTC |
| `helpful_vote` | `BIGINT` | Helpful-vote count |
| `verified_purchase` | `BOOLEAN` | Purchase verification flag |

Reviews use the composite primary key **(`source_id`, `source_line`)**.

The intended relationship is one product to many reviews through `parent_asin`. 

The schema initially creates the tables without a foreign key; the loader's `cleanup_reviews()` function adds `reviews_product_fk` after loading.

Images and videos are excluded from the relational model. Product `author`, `subtitle`, and `bought_together` fields are also excluded.

### Data Validation & Loading

[util.py](Phase%201/Create%20and%20Load%20Dataset/util.py) implements the data-cleaning helpers:

- `read_json()` streams records with their original line numbers and marks malformed JSON or non-object records as invalid.
- `text()` converts missing, blank, or non-string values to `None` and cleans unsupported characters.
- `number()` validates finite, nonnegative numbers, ratings between 1 and 5, integer counts within the signed `BIGINT` range, and prices within the schema's decimal range.
- `boolean()` accepts only actual `True` and `False` values.
- `review_time()` converts Unix milliseconds into a UTC datetime.
- `json_value()` checks the expected container type, cleans nested values, and serializes lists or dictionaries for MySQL.

[load_data.py](Phase%201/Create%20and%20Load%20Dataset/load_data.py) provides product and review loaders. Both skip records without a usable `parent_asin`, insert records in **5,000-row batches**, and commit each completed batch. Invalid optional values become SQL `NULL`; empty JSON containers remain intact. Reviews can be retained even when their text is missing.

Duplicate primary keys are skipped using `ON DUPLICATE KEY UPDATE` statements that leave the existing row unchanged. UTC timestamps are stored without timezone information in `DATETIME(3)` columns.

### Running Phase 1

Run commands from the project root so the scripts can locate the dataset folder.

1. Install Python 3 and have a running MySQL server with JSON-column support and the MySQL command-line client. Install the Python connector:

   ```bash
   python3 -m pip install mysql-connector-python
   ```

2. Download and place the two source files in `Amazon Electronics Dataset/`.

3. Generate the profiling reports:

   ```bash
   python3 "Phase 1/Profile Dataset/profile_data.py"
   ```

4. Create the database and tables:

   ```bash
   mysql -u root -p < "Phase 1/Create and Load Dataset/schema.sql"
   ```

5. Update the connection settings in `load_data.py` for your local MySQL installation. The current settings use `localhost`, user `root`, an empty password, and database `amazon_electronics_reviews`.

6. For an initial full import run:

   ```bash
   python3 "Phase 1/Create and Load Dataset/load_data.py"
   ```

The foreign-key addition is a one-time step. For subsequent imports, adjust the cleanup call so it does not attempt to add the existing constraint again.

---

> **Note:** AI assistance was used in generating code comments and documentation throughout this project.
