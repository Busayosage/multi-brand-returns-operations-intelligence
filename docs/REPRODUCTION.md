# Reproduce the published analytical baseline

This package rebuilds the retail database and dashboard input CSVs. It does not recreate Tableau's manually authored layout or publish anything. The original recovered scripts are retained with their analytical rules unchanged. Use the orchestrator below: individual scripts still have historical default paths and must receive explicit arguments for a new run.

## Acquire the source

Download **Online Retail II** from [UCI dataset 502](https://archive.ics.uci.edu/dataset/502/online+retail+ii), choose Download and extract `online_retail_II.xlsx`. Attribution: Chen, D. (2012), Online Retail II, DOI [10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D). UCI lists CC BY 4.0. Use the original two-sheet workbook, not the single-year Online Retail dataset. No login or credential is required.

Place it at `Data/Raw/online_retail_II.xlsx` (ignored by Git). The recovered source used in the 23 October test is 45,622,278 bytes, SHA-256 `bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980`. The sheets must be `Year 2009-2010` and `Year 2010-2011`, with columns Invoice, StockCode, Description, Quantity, InvoiceDate, Price, Customer ID, Country. If a later UCI download differs, retain it separately and investigate before claiming the same baseline.

The source has 1,067,371 rows. The approved one-for-one cross-sheet occurrence rule excludes 22,523 overlapping occurrences and retains 1,044,848 lines. Within-sheet repeats remain; they are flagged, not broadly deleted. No raw data, customer-level extract, SQLite database or Tableau binary belongs in GitHub.

## Environment and complete run

Run SQLite on a local disk outside a cloud-synchronised folder; sync or archive only after all database handles close. A retained journal in the first synced-workspace run prevented read-only reopening. For example, use `/tmp/returns-reproduction-new` on Linux (temporary; copy the final evidence somewhere durable afterwards).

Use Python 3.12; the recorded test uses 3.12.14. Dependencies are pandas, openpyxl and numpy (numpy is imported directly by the eligibility stage). SQLite and the remaining modules are in the standard library. `requirements-verified.txt` records the exact installed versions for this verification; `requirements.txt` remains a broader supported range, not a claim that every version combination has been tested. Allow at least 8 GB RAM and 10 GB free disk for retained CSV intermediates, audits and database; actual use is documented in the verification report.

```bash
python -m venv .venv
# Linux/macOS
.venv/bin/python -m pip install -r requirements-verified.txt
.venv/bin/python src/reproduce.py --input Data/Raw/online_retail_II.xlsx --run-dir /tmp/returns-reproduction-new
# Windows PowerShell: use .venv\Scripts\python.exe and replace /tmp/returns-reproduction-new
# with a new local path such as C:\Temp\returns-reproduction-new, outside OneDrive/cloud sync
```

`--run-dir` must not exist. All stages run in separate processes using that environment, with explicit paths, no network access and no overwrite of an existing database. The orchestrator records a stage log, exit code and timing, and stops on the first failure. Do not use a failed directory as the validated result or rename it to hide a failed run. Fix the problem and run into a new directory. Timestamped folders and absolute paths make audit JSON/checksums differ between runs; analytical values and source fields are the comparison targets, not byte identity of every metadata file.

## Execution and dependency order

Each stage's CSV must stay beside its companion JSON; the following scripts verify those checksums before proceeding. The runner records the generated folder names in `run_manifest.json`.

| Order | Script in src | Required input / companion | Principal output |
|---|---|---|---|
| 1 | resolve_cross_sheet_duplicates.py | Original workbook, both sheets | cross_sheet_*/transactions_after_cross_sheet_matching.csv + matching_summary.json; exclusion and repetition audits |
| 2 | flag_missing_customer_ids.py | Stage 1 CSV + matching_summary.json | customer_id_*/transactions_with_customer_id_flag.csv + customer_id_summary.json |
| 3 | flag_missing_descriptions.py | Stage 2 CSV + customer_id_summary.json | description_*/transactions_with_description_flag.csv + description_summary.json |
| 4 | flag_price_exceptions.py | Stage 3 CSV + description_summary.json | price_*/transactions_with_price_flags.csv + price_summary.json |
| 5 | classify_transaction_patterns.py | Stage 4 CSV + price_summary.json | transaction_patterns_*/transactions_with_pattern_classification.csv + transaction_pattern_summary.json |
| 6 | correct_bad_debt_classification.py | Stage 5 CSV + summary | bad_debt_correction_*/transactions_with_corrected_accounting.csv + bad_debt_correction_summary.json |
| 7 | classify_stock_codes.py | Stage 6 CSV + summary | stock_codes_*/transactions_with_stock_code_categories.csv + stock_code_summary.json |
| 8 | build_quality_review.py | Stage 7 CSV + summary | quality_review_*/quality_review_summary.json and audit reports; no transaction replacement |
| 9 | define_kpi_eligibility.py | Stage 7 CSV/summary + stage 8 quality_review_summary.json via --review | kpi_eligibility_*/transactions_with_kpi_eligibility.csv + kpi_eligibility_summary.json + KPI_DEFINITIONS_v1.md |
| 10 | calculate_kpis.py | Stage 9 CSV + summary + policy document | kpis_*/kpi_summary.json, invoice_consistency_audit.csv, KPI reports and repetition sensitivity |
| 11 | review_invoice_keys.py | Stage 9 CSV/summary + stage 10 directory via --prior-kpis | invoice_review_*/invoice_review_summary.json, kpi_overall_reviewed.csv, kpi_monthly_reviewed.csv, rule and audits |
| 12 | import_to_sqlite.py | Stage 9 CSV/summary + stage 11 directory via --review-dir | database/retail_analytics.db + sqlite_import_*.json |
| 13 | export_dashboard_data.py | Newly validated database via --database; --output-root outputs | dashboard_export_*/dashboard_transactions.csv, kpi_reference.csv, validation_report.json, README_dashboard.md |
| 14 | part2_returns_intelligence.py | Database via --db; new --output-dir | part2/part2_results.json and synthetic_returns_cases.csv; --count 5000 --seed 2026 |

All stage paths above are relative to the new run directory. For stages 1–11, `--input` is the listed input and `--output` is its `outputs` directory. The runner's `STAGES` list and subsequent explicit calls are executable examples of every argument. Stage 12 rejects a database that already contains objects. Stages 13 and 14 open the database read-only. Use a new Part 2 output directory because its standalone command permits replacing its own CSV/JSON outputs.

The accounting correction changes three classification cells on exactly one reviewed row (`Year 2010-2011!299984`); it preserves the original positive price. Eligibility policy v1.0 is provisional: digit-leading stock codes are candidate merchandise, specific non-merchandise categories remain separate, and unassessed descriptions do not become verified products. Invoice rule v1.1 accepts same-day timestamp variations up to ten minutes with consistent nonblank country/customer; this is a documented analytical threshold, not a source-system guarantee. Orders remain invoice proxies.

## SQL analysis after import

Run `python src/verify_reproduction.py --run-dir /tmp/returns-reproduction-new --saved-validation PATH_TO_RECOVERED_VALIDATION_JSON` to execute all reviewed queries and compare the export with the saved baseline when that local evidence is available. Omit `--saved-validation` if independently reproducing without private Drive access; reference constants and the export's internal reconciliation are still checked. Optional `--expected-synthetic PATH_TO_RECOVERED_SYNTHETIC_CSV` checks exact generator output bytes.

SQL 03–17 are independent read-only analytical queries over the imported database, not database migrations. Numeric order is a useful review narrative: 03 monthly KPIs; 04 year-on-year months; 05 Jan–Nov totals; 06 cancellation ratio; 07 product concentration; 08–09 source-record inspection; 10 both-record sensitivity; 11–12 country and reconciliation; 13–14 Australia customer detail; 15–16 EIRE detail; 17 combined cancellation checks. SQL 17 has four statements, so do not run it using a single-statement-only API. No SQL 01/02 was recovered or required: the importer creates tables, views and indexes. SQL uses integer thousandths of GBP and the verifier rejects any other money scale. Detailed query output remains local and ignored.

## Acceptance evidence and expected results

- Cross-sheet count 22,523 excluded; 1,044,848 retained; unique provenance, source workbook unchanged.
- Only the approved one-row accounting classification correction; all source values preserved.
- Invoice review: 83 accepted timestamp variations, zero unresolved invoice keys.
- Import: money scale 1000; all source fields read back; integrity/foreign keys pass; overall and 25 monthly reports reconcile.
- Export: PASS, all CSV fields read back, eight exact measures reconciled over 28 scopes (overall + 25 months + two Jan–Nov periods), eligibility counts reconcile.
- Jan–Nov 2010/2011 gross integer units 8,628,418,424 / 8,878,008,023; cancellation 221,407,480 / 286,989,560; orders 18,077 / 17,407. Net GBP £8,407,010.944 / £8,591,018.463; cancellation ratios 2.57% / 3.23%.
- Product 23166 cancellation-marked value £77,479.64. Reviewed pair is £77,183.60 in each direction, sixteen minutes apart. Excluding BOTH rows yields 2.38% while preserving net value; do not change the headline or delete these rows.
- Australia net change £106,675.50; EIRE −£81,105.23. Customer analysis is concentration, not proven cause.
- Synthetic seed 2026: 5,000 fictional cases; 96.72% resolved within seven days, 164 late, median 5.07 days. Carrier/hub and late-week effects are coded assumptions; no real source transaction links, measured operating costs or realised benefits.

Run existing tests with the rebuilt database:

```bash
PART2_DB=/tmp/returns-reproduction-new/database/retail_analytics.db .venv/bin/python -m unittest discover -s tests -v
```

In PowerShell, set `$env:PART2_DB` to the same path before running unittest. The test suite otherwise skips the data-backed test; a skipped test is not a pass on source data.

## Use the outputs in Tableau

Use `dashboard_transactions.csv` as the observed transaction datasource, preserving identifier fields as text and ISO dates. Do not join `kpi_reference.csv`: it is an independent QA table. Do not filter the entire datasource to sales-only, which would remove cancellation values. Sum integer/GBP numerators first, then calculate ratios and AOV; never average row or monthly ratios. Blank customers are unknown, not one identified customer. December 2011 is partial and excluded from comparable Jan–Nov findings.

Use `synthetic_returns_cases.csv` as an entirely separate datasource. The generated workbook-layout script in Drive is an archival construction tool and is deliberately excluded: later manual Tableau corrections supersede it, so it cannot reproduce the published layout accurately. Obtain the current published workbook via Tableau's Download control if available, retain a dated backup, then connect a working copy to the generated files. This phase does not overwrite the live workbook.

See [verification](VERIFICATION_2026-10-23.md) for actual results and [Tableau QA](TABLEAU_QA_2026-10-23.md) for the tested experience and remaining limitations. Cancellation markings do not establish physical returns or their causes. Improvement controls remain proposals.
