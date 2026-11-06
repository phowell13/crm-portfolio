"""
Run a .sql file against the synthetic data, locally, with DuckDB.

The CSVs in data/raw/ are loaded as tables. The email tables are also exposed
under their Salesforce Marketing Cloud data view names, so you can write
queries the way you would in an SFMC Query Activity:

    _Job, _Sent, _Open, _Click

Usage:
  python scripts/run_sql.py sql/00_smoke_test.sql
  python scripts/run_sql.py sql/01_engagement_score.sql --out data/output/engagement_score.csv

Dialect note: SFMC runs SQL Server (T-SQL). DuckDB is very close for this kind
of work, but a few functions differ, e.g.
  T-SQL  DATEDIFF(day, a, b)      DuckDB  date_diff('day', a, b)
  T-SQL  SELECT TOP 10 ...        DuckDB  SELECT ... LIMIT 10
  T-SQL  GETDATE()                DuckDB  use the fixed AS_OF date below
Keep a note of any differences in DECISIONS.md. Showing you know them is a plus.
"""

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
AS_OF = "2026-10-31"  # matches generate_data.py

SFMC_VIEWS = {"_Job": "job", "_Sent": "sent", "_Open": "open", "_Click": "click"}


def connect():
    if not RAW.exists():
        raise SystemExit("No data yet. Run: python scripts/generate_data.py")
    con = duckdb.connect()
    for csv in sorted(RAW.glob("*.csv")):
        path = str(csv).replace("'", "''")
        con.execute(f"CREATE VIEW \"{csv.stem}\" AS SELECT * FROM read_csv_auto('{path}')")
    for view, table in SFMC_VIEWS.items():
        con.execute(f'CREATE VIEW "{view}" AS SELECT * FROM "{table}"')
    # handy constant so queries don't depend on the real date
    con.execute(f"CREATE MACRO as_of() AS DATE '{AS_OF}'")
    return con


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sql_file")
    ap.add_argument("--out", help="save the result of the final statement to this CSV")
    ap.add_argument("--rows", type=int, default=20, help="rows to print")
    args = ap.parse_args()

    con = connect()
    sql = Path(args.sql_file).read_text()
    statements = [s for s in sql.split(";") if s.strip() and not all(
        line.strip().startswith("--") or not line.strip() for line in s.splitlines())]
    if not statements:
        raise SystemExit("No SQL statements found (only comments?).")
    for stmt in statements[:-1]:
        con.execute(stmt)
    df = con.execute(statements[-1]).df()

    print(df.head(args.rows).to_string(index=False))
    print(f"\n{len(df):,} rows")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.out, index=False)
        print(f"Saved to {args.out}")


if __name__ == "__main__":
    main()
