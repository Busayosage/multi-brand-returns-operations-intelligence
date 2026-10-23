# Multi-Brand Returns Operations Intelligence

**Independent portfolio project · Python · SQL · Tableau · Retail, Logistics & Continuous Improvement**

> **Status: Tableau showcase published — 19 October 2026.** Explore six dashboard pages covering retail performance, country and customer concentration, cancellation exceptions, a separate synthetic logistics demonstration, and proposed improvement controls. This review branch recovers the downstream pipeline and documents an isolated rebuild; see the dated verification report for actual test results and limitations. The synthetic generator was already present in the Part 2 release.

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

## Reproduction package

- Fourteen recovered analytical Python scripts, plus a portable orchestrator and verifier.
- Fifteen reviewed read-only SQL files (03–17), KPI policy, source dictionary and Part 2 tests.
- Explicit source acquisition, dependency versions, intermediate files and execution order in [Reproduction](docs/REPRODUCTION.md).
- [Verification evidence](docs/VERIFICATION_2026-10-23.md) and [published Tableau QA](docs/TABLEAU_QA_2026-10-23.md), with failures and unverified items identified.
- No raw extracts, database, credentials, customer-level outputs or packaged Tableau workbooks. Generated outputs stay local; the live workbook is linked above.

Download the original two-sheet workbook from UCI, create a fresh Python 3.12 environment and install `requirements-verified.txt`. Then run:

```bash
python src/reproduce.py --input Data/Raw/online_retail_II.xlsx --run-dir /tmp/returns-reproduction-new
```

Use a **new local directory outside cloud sync** for SQLite. The guide provides Windows instructions, every stage dependency and the follow-up validation command. This rebuild produces data, SQL results and fictional logistics inputs; Tableau's manually corrected presentation is a separate artifact.

## Roadmap

1. **Retail Performance:** source profiling, validation, reconciled KPIs and polished Tableau dashboard.
2. **Returns & Logistics:** published cancellation exception views and a separately labelled **synthetic** 5,000-case logistics demonstration; generator and complete downstream workflow recovered on this review branch.
3. **Root Cause:** Pareto and exception investigations with evidence separate from hypotheses.
4. **Continuous Improvement:** Lean process mapping, monitored recommendations and potential improvement scenarios.
5. **Portfolio publishing:** Tableau Public showcase is live; review this branch and resolve the recorded presentation limitations before any separate live-workbook correction.

See [Project Status](docs/PROJECT_STATUS.md) for verified versus planned deliverables. No source data or private customer records are included in the repository.
