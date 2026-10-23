# Reviewed retail diagnostics

SQL 03–17 run after `import_to_sqlite.py`. They are read-only SELECT/CTE queries, not migrations; no SQL 01/02 is required. The importer creates the schema. Run in numeric order for the analytical narrative; query results do not feed later queries. SQL 17 contains four statements. Money uses integer thousandths of GBP; the verifier checks scale=1000. See [the full workflow](../docs/REPRODUCTION.md). Query output may contain public-source customer/invoice detail and stays outside GitHub.
