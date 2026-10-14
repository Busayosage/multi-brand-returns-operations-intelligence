# Multi-Brand Returns Operations Intelligence

**Independent portfolio project · Python · SQL · Tableau · Retail, Logistics & Continuous Improvement**

> **Status: In development.** This first public release includes recovered data-quality scripts and project documentation. The completed Tableau workbook, later SQL export pipeline and synthetic logistics model are not yet included.

## Project objective

Build a reusable analytical framework to evaluate retail transaction performance, investigate cancellation-marked records, design a returns/logistics intelligence layer, and identify measurable continuous improvement opportunities.

**Source:** [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii), a public retail transaction dataset. This is an independently developed portfolio, **not an employer or ReBound project**.

## Historical retail performance findings

Comparable January–November periods, from the previously documented Tableau/SQL reconciliation (not re-executed for this release):

| KPI | 2010 | 2011 |
| --- | ---: | ---: |
| Net merchandise value | £8,407,010.94 | £8,591,018.46 |
| Sales orders | 18,077 | 17,407 |
| Average order value | £477.31 | £510.03 |
| Cancellation-marked value ratio | 2.57% | 3.23% |

**Analytical question:** Why did recorded net merchandise value increase by ~2.2% while sales orders decreased by ~3.7%? A cancellation prefix is not proof of a physical return; net merchandise value is not profit.

## What is included

- Five recovered Python scripts for cross-sheet occurrence matching, missing customer IDs, missing descriptions, price exceptions and transaction-pattern classification.
- Source data dictionary, data methodology and progress notes.
- A conservative `.gitignore` to exclude source workbooks, CSV/Parquet extracts, local databases, Tableau packaged workbooks, credentials and caches.
- A development roadmap describing upcoming SQL, Tableau, logistics and continuous improvement stages.

**Verification:** the five scripts passed Python syntax compilation; their complete execution against original data has not been rerun as part of this GitHub release. Do not treat missing downstream artifacts as completed.

## Reproduction

```bash
python -m venv .venv
# Activate the environment for your system
pip install -r requirements.txt
python src/resolve_cross_sheet_duplicates.py --input "Data/Raw/online_retail_II.xlsx" --output outputs
```

Download the original workbook from UCI. The later scripts depend on audited outputs and companion summary JSON files from previous processing stages; select the appropriate input with `--input` rather than inventing earlier data.

## Roadmap

1. **Retail Performance:** source profiling, validation, reconciled KPIs and polished Tableau dashboard.
2. **Returns & Logistics:** examine cancellation exceptions and later add clearly labelled **synthetic** carrier, warehouse and SLA data.
3. **Root Cause:** Pareto and exception investigations with evidence separate from hypotheses.
4. **Continuous Improvement:** Lean process mapping, monitored recommendations and potential improvement scenarios.
5. **Portfolio publishing:** tested reproducible SQL, Tableau Public dashboard, diagrams, and further case-study writeups.

See [Project Status](docs/PROJECT_STATUS.md) for verified versus planned deliverables. No source data or private customer records are included in the repository.
