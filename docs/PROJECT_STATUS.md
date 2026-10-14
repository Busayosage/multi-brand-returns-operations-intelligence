# Project Status — 14 October 2026

## Verified in recovered files
- Public UCI Online Retail II is the transaction source.
- Five Python source scripts are recovered from the original project Drive folder; all have passed syntax compilation, **not a full dataset execution in this release**.
- Data dictionary and a historical analytical checkpoint are available.
- Tableau screenshots show a 1400×900 Retail Performance dashboard with navy navigation sidebar, four KPI comparisons, monthly merchandise-value trend, and pending legend/card styling. No Tableau workbook is committed yet.

## Historical reconciliation (not rerun for this publication)
- 1,067,371 source rows; 22,523 matched cross-sheet overlap occurrences removed; 1,044,848 retained.
- Full-scope reported net merchandise value: £18,981,261.52. Full-scope 39,516 eligible sales orders.
- January–November comparison 2010 versus 2011: net merchandise £8,407,010.94 versus £8,591,018.46; AOV £477.31 versus £510.03; cancellation ratio 2.57% versus 3.23%; orders 18,077 versus 17,407.
- Investigated a large cancellation-marked product 23166 transaction; reason and physical return status remain unknown.

## Missing artifacts to recover
- Local database `database/retail_analytics.db`.
- Later `export_dashboard_data.py` and generated `dashboard_transactions.csv`, `kpi_reference.csv`, `validation_report.json`.
- SQL views and Tableau workbook (`.twb`/`.twbx`).

## Next development milestones
1. Recover and verify local SQL and Tableau export pipeline; ensure no raw data is committed.
2. Finish Retail Performance Tableau styling, legends, navigation and interactivity.
3. Build and validate a **synthetic**, clearly marked logistics enrichment layer and associated service metrics.
4. Document root-cause and continuous improvement cases and maintain real-versus-simulated boundaries.

**Project ownership:** independent portfolio; an earlier interview inspired part of the scope but no employer data or affiliation is claimed.
