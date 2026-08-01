"""
Run the Stage 3 SQL metric analysis through DuckDB.

This script does NOT compute any metrics itself — it only reads
sql/03_metric_analysis.sql, executes each labeled block in order, prints the
data-quality check, and saves the three analytical query outputs to CSV.
All metric logic lives in the .sql file.
"""

import re
from pathlib import Path

import duckdb

ROOT_DIR = Path(__file__).resolve().parent.parent
SQL_PATH = ROOT_DIR / "sql" / "03_metric_analysis.sql"
OUTPUT_DIR = ROOT_DIR / "outputs" / "sql"

# Blocks whose result should be saved as a CSV output (setup and
# data_quality are run but not saved as one of the three requested files).
SAVED_BLOCKS = {
    "overall_metrics": "overall_metrics.csv",
    "segment_metrics": "segment_metrics.csv",
    "daily_metrics": "daily_metrics.csv",
}


def parse_blocks(sql_text: str) -> dict:
    """Split the SQL file on '-- @block: <name>' markers."""
    pattern = re.compile(r"-- @block:\s*(\w+)\s*\n")
    parts = pattern.split(sql_text)
    # parts = [preamble, name1, sql1, name2, sql2, ...]
    blocks = {}
    for i in range(1, len(parts), 2):
        name = parts[i]
        query = parts[i + 1].strip()
        blocks[name] = query
    return blocks


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sql_text = SQL_PATH.read_text(encoding="utf-8")
    blocks = parse_blocks(sql_text)

    con = duckdb.connect()

    # 'setup' creates the ab_test_data view; no result to fetch.
    con.execute(blocks["setup"])

    print("=== Data quality checks ===")
    data_quality_df = con.execute(blocks["data_quality"]).df()
    print(data_quality_df.to_string(index=False))

    for block_name, filename in SAVED_BLOCKS.items():
        df = con.execute(blocks[block_name]).df()
        out_path = OUTPUT_DIR / filename
        df.to_csv(out_path, index=False)
        print(f"\n=== {block_name} ({len(df)} rows) -> {out_path} ===")
        print(df.to_string(index=False))

    con.close()


if __name__ == "__main__":
    main()