# Multi-Brand Returns Operations Intelligence

**Independent portfolio project · Python · SQL · Tableau · Retail, Logistics & Continuous Improvement**

> **Status: Tableau showcase published — 19 October 2026.** Explore six dashboard pages covering retail performance, country and customer concentration, cancellation exceptions, a separate synthetic logistics demonstration, and proposed improvement controls. The repository contains the recovered data-quality scripts and documentation; the full downstream SQL/export pipeline and logistics generator are not included in this code release.

**[Open the interactive Tableau Public workbook](https://public.tableau.com/app/profile/oluwasbusayomi.oseola/viz/Returns_Intelligence_20261019_Checked/RetailPerformance_)**

## Project objective

Build a reusable analytical framework to evaluate retail transaction performance, investigate cancellation-marked records, design a returns/logistics intelligence layer, and identify measurable continuous improvement opportunities.

**Source:** [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii), a public retail transaction dataset. This is an independently developed portfolio project using public retail transaction data.

## Validated retail performance findings

Comparable January–November periods. The recovered database aggregates were recomputed on 16 October 2026 and matched the saved validation report across all 28 scopes; this was not a fresh raw-workbook-to-database validation.

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
- A development roadmap and [Tableau guide](tableau/README.md) linking the published six-page workbook.
- Clearly separated observed transaction findings, fictional logistics metrics, and proposed improvement controls.

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
2. **Returns & Logistics:** published cancellation exception views and a separately labelled **synthetic** 5,000-case logistics demonstration; publish the reviewed generator and full reproduction workflow in a later code release.
3. **Root Cause:** Pareto and exception investigations with evidence separate from hypotheses.
4. **Continuous Improvement:** Lean process mapping, monitored recommendations and potential improvement scenarios.
5. **Portfolio publishing:** Tableau Public showcase is live; extend the repository with reviewed SQL, downstream scripts and further reproducibility documentation.

See [Project Status](docs/PROJECT_STATUS.md) for verified versus planned deliverables. No source data or private customer records are included in the repository.
