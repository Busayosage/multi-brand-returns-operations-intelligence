# Verification — 23 October 2026

## Actual result

A fresh Python 3.12.14 virtual environment rebuilt the recovered two-sheet UCI workbook through **all 14 stages successfully** in a new local directory outside cloud sync. Analytical source scripts were recovered unchanged from Drive. Total stage runtime: 284.57 seconds; retained outputs/audits/database: 3,317,430,591 bytes (about 3.09 GiB). This is one Linux environment, not a claim of cross-platform certification.

| Check | Result |
|---|---|
| Dependency installation and syntax compilation | PASS; exact versions in requirements-verified.txt |
| Raw input unchanged | PASS; SHA-256 bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980 |
| Cross-sheet occurrence matching | PASS; 22,523 excluded, 1,044,848 retained, within-sheet repetitions retained |
| Downstream classifications, quality, eligibility, KPI and invoice review | PASS; companion checksums/readbacks and original-field preservation checks passed; 83 accepted invoice timestamp variations, zero unresolved |
| SQLite import | PASS; exact scale 1000, all source-field readback, overall + 25 monthly reconciliations, integrity and foreign keys |
| Dashboard export | PASS; every field read back; eight exact measures in 28 scopes |
| Comparison to saved original validation JSON | PASS; all 28 scopes and eligibility counts identical |
| Dashboard transaction CSV byte checksum | PASS; cd353f83e7bb91ec217b07d84042f2a4d3057d4de278049de7257242a0a3a145 matches saved validation |
| KPI reference CSV byte checksum | PASS; fc76f0b19c5a35f1ccb01779d3d92b0d34868e3392c27c099009e991f62647f8 matches saved validation |
| Reviewed downstream SQL | PASS; 15 files, 18 statements executed in read-only mode; country/product/sensitivity references checked |
| Synthetic generator | PASS; 5,000 cases, seed 2026; CSV byte-identical to recovered original; 96.72% within seven days, 164 late, median 5.07 days |
| Existing unit tests with PART2_DB set to rebuilt database | PASS; 5 tests, none skipped, 2.188 seconds |
| Existing run directory refusal | PASS; FileExistsError, original run retained |
| Populated database refusal | PASS; importer rejects existing objects; database SHA unchanged |
| Verification read-only guarantee | PASS; database SHA unchanged after SQL checks |

New database SHA-256: `8203715befdc7579395a8a956af32c604c5f4100796642f39453a5e86ab3efae`. Do not expect byte equality of databases whose import metadata/path/checksums differ. The strong baseline comparison here is exact exported transaction CSV equality plus all saved aggregate scopes. The generated README_dashboard.md differs only in line endings from the saved guide: normalising CRLF to LF yields identical text. Its byte hash differs; analytical data bytes match.

Machine-readable summary: [verification_results_2026-10-23.json](verification_results_2026-10-23.json). Recovery source hashes and initial GitHub comparison: [recovery_source_manifest.json](recovery_source_manifest.json). Full per-row SQL results and local paths are excluded from the public repository.

## Failed checks and recovery limitations

1. The Drive database ZIP passes ZIP CRC, but its 600,113,152-byte SQLite member reports `database disk image is malformed`. It is not a usable baseline. Neither the archive nor the separate saved database was changed.
2. The separate 662,708,224-byte saved database could not be downloaded through the connector: HTTP 413, above its 268,435,456-byte limit. No fresh direct integrity claim is made for that file. Its earlier checkpoint validation is historical evidence.
3. The first pipeline run in the synced workspace passed stages 1–13, then Part 2 failed at read-only quick_check with `attempt to write a readonly database`. A journal and temporary files were still present. That failed run was retained. A complete rerun outside sync passed without changing analytical code. The journal association is an environmental inference, not a demonstrated SQLite engine defect. The guide now requires a local non-synced run directory.
4. Windows/macOS execution and every supported dependency combination were not tested. The recovered source was used; a fresh UCI download was not separately hash-compared during this run. UCI's official acquisition page was checked.
5. The data pipeline reconstructs dashboard inputs, not the manually authored Tableau layout. Downloaded workbook QA and Hyper recalculation equivalence are separate scopes; no claim of a raw-to-live-Tableau automatic deployment.

## Preserved boundaries

Jan–Nov 2010/2011 net value £8,407,010.944 / £8,591,018.463; orders 18,077 / 17,407. Headline cancellation ratio 3.23% remains; 2.38% is sensitivity excluding BOTH reviewed records, with unchanged net. Cancellation markings do not prove physical returns or causes. Fictional logistics outputs are independent. Controls remain proposed, with no measured benefit claim.

## Checkpoint and next step

Completed: source comparison, recovery, documentation, clean rebuild, SQL execution, byte/aggregate comparisons, existing tests and no-overwrite checks. Main and the live workbook remain unchanged. Changes are prepared on `review/reproducibility-2026-10-23`.

Next: complete the desktop/narrow Tableau experience report, attach its remaining limitations, review the branch diff and merge only through a separate review decision. Any later Tableau correction must start from the dated backup and undergo a new visual/interaction check before publication.
