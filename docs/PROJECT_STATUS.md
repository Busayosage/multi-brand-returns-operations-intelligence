# Project Status — 19 October 2026

Independent portfolio: Multi-Brand Returns Operations Intelligence.


## Tableau publication and walkthrough — 19 October 2026

- [Live six-page Tableau Public showcase](https://public.tableau.com/app/profile/oluwasbusayomi.oseola/viz/Returns_Intelligence_20261019_Checked/RetailPerformance_).
- Retail, country, customer, cancellation, synthetic logistics and improvement-roadmap views were opened and rendered in the desktop browser.
- The 5,000-case logistics model is fictional and separate from observed transactions. The improvement controls remain proposals; no realised benefits or proven cancellation causes are claimed.
- A 1 minute 50 second narrated video, including captions and captured dashboard views, was created and approved by the owner for LinkedIn publication. The public post URL will be recorded after publication.
- README and the Tableau guide now link the live workbook. Full downstream SQL/export code and the synthetic generator have not been added to this code release.
- Phone layout and comprehensive tooltip/filter/reset acceptance testing remain outstanding.

## Recovery milestone verified
- Recovered the original retail_analytics.db from the user's compressed Google Drive upload.
- SQLite PRAGMA quick_check returned ok; database opened in read-only mode.
- source_transactions contains 1,044,848 rows.
- Recomputed all eight aggregate measures in all 28 scopes of the saved validation_report.json (overall, 25 months, and two Jan–Nov scopes): 28/28 matched.
- This verifies recovered database aggregates against the saved export report. It is not a fresh raw-workbook-to-database or CSV field-by-field validation.
- Database SHA-256: d601c1c9630669c2c07847e885e5622cef6170468f6611728d366e1449416604.
- Located 13 Python scripts, 14 SQL files, Tableau workbook versions, CSV export and supporting records in the uploaded project folder. Their presence does not mean every script or workbook has been rerun/reviewed.

## Recomputed comparable January–November results
| Metric | 2010 | 2011 |
|---|---:|---:|
| Gross merchandise value | £8,628,418.424 | £8,878,008.023 |
| Cancellation-marked value | £221,407.480 | £286,989.560 |
| Net merchandise value | £8,407,010.944 | £8,591,018.463 |
| Eligible sales orders | 18,077 | 17,407 |

Money stored as exact integers at scale 1000; round for presentation only.
AOV uses gross merchandise value / eligible sales orders. Cancellation-marked activity is not proof of physical returns; net merchandise value is not profit.

## Publication
Part 1 published and verified on 15 October 2026:
https://www.linkedin.com/feed/update/urn:li:activity:7516409731381374976/

Further posts follow verified project milestones, not the expired Wednesday–Friday schedule.

## Historical next milestones recorded on 16 October
1. Review recovered cancellation SQL and Tableau calculations against this verified baseline; preserve reviewed-pair headline/sensitivity distinction.
2. Finalise existing Retail Performance dashboard.
3. Define and build a separately labelled synthetic logistics layer; validate links, dates, quantities and service metrics before presenting results.
4. Develop evidence-led Pareto/root-cause investigations, process mapping and measurable continuous-improvement proposals. Keep hypotheses and simulated benefits explicit.
5. Publish reviewed code/results to GitHub, then prepare Parts 2 and 3.

Raw data, database, full CSV and private environment files are not committed to this repository.
