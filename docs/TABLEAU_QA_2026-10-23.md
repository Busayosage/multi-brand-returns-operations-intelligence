# Published Tableau experience — 23 October 2026

This is a read-only review of the [published workbook](https://public.tableau.com/app/profile/oluwasbusayomi.oseola/viz/Returns_Intelligence_20261019_Checked/RetailPerformance_). No authoring, republishing, sheet deletion or data refresh was performed. Last Published Date still reads 19 October 2026.

A fresh current-version workbook was downloaded before any possible correction and saved to the existing Drive `tableau` folder: [23 October QA backup](https://drive.google.com/file/d/1uavl7MuxZQ53dBCsX57HcwW1B34I7yWQ/view?usp=drivesdk). Size 17,392,532 bytes; ZIP CRC passes; SHA-256 `2a44e4e8d7e147edef0c35e2d9b14e829bc4b135508f438d08a55c480a827ced`. Contains the TWB and two separate Hyper extracts. Previous backups remain intact. The download listener timed out, but the completed downloaded file was subsequently found, validated and saved; no duplicate download was requested.

## Actual desktop checks

Chrome viewport reported 1363 × 936 CSS pixels; embedded viz width 1140. The Explore Vizzes panel initially obscured the right side; closing it exposed the full embedded width. Every intended dashboard was opened with the published tab controls and visually inspected. Keyboard Enter reliably activated the tabs; pointer activation was not consistently verified through this automation environment, so this is not a mouse-navigation acceptance claim.

| Page / interaction | Observed result |
|---|---|
| Retail Performance | Loads all four KPI cards and Jan–Nov line chart. Values match the baseline at displayed precision. The +2.2% growth text is visibly clipped. Legend still says Year of Transaction Date. |
| Country Performance | Loads; Australia £106,675.50 visible. Vertical scrolling exposes EIRE −£81,105.23. Bottom explanatory text is clipped within its text zone at this width. |
| Customer Concentration | Both panels load, including customer 12415 £104,169.34 and 14156 −£59,640.90. Bottom note clips part of the missing-ID/scales/cause caveat. |
| Cancellation Analysis | Loads product concentration, equal/opposite pair and the separate BOTH-record sensitivity. Some KPI third-line changes and the lower investigation note clip. Headline remains 3.23%; sensitivity 2.38%. |
| Synthetic Logistics | Loads 5,000, 96.7%, median 5.07, 164; separate synthetic banner and assumptions visible. Chart headings distinguish average from median. |
| Improvement Roadmap | Loads; proposed controls and no realised benefits are explicit. Text is readable at the desktop width tested. |
| Tooltip: retail | Keyboard mark navigation/tooltip shows January 2010 net merchandise £606,385.18 with year and month. |
| Tooltip: country | Australia 2011 difference £106,675.50. Wording is technical, but value/context are present. |
| Tooltip: customer | Customer 12415, 2011 difference £104,169.34. Technical Tableau table-calculation wording remains. |
| Tooltip: cancellation | Product 23166 shows 77,480 (rounded whole-pound display); the exact value is £77,479.64 in validation. GBP is supplied by chart title/axis. |
| Tooltip: synthetic carrier | Carrier A accessible tooltip says Avg. On Time 100%, while the chart label shows 99.6%. This is a precision/presentation defect, not evidence of a 100% SLA result. |
| Mark selection / clearing | Retail Space produces “Mark selected”; Control+Space produces “Mark deselected”. |
| Revert | Enabled after session interactions; Enter resets interaction history and disables Revert. A selected-axis prompt can remain: Revert is not certified as clearing every visual selection. Use the verified mark toggle to clear a mark. |
| Available filters | No authored quick-filter controls or dashboard filter actions in the public pages. XML inspection confirms zero filter zones and no dashboard actions. Generic Tableau context commands such as Keep Only/Exclude can appear on a selected legend; those were observed but not executed/certified. |
| Sidebar | Plain text directory explicitly points to the published tabs; it is not a set of navigation buttons. No broken-sidebar-button claim. |

Tab order remains Customer, Cancellation, Country, Retail, Synthetic, Improvement; trailing full stops remain. All six are accessible through tabs, but the order is a presentation improvement opportunity.

## Narrow/mobile verification boundary

**Not verified in a narrow viewport or on mobile hardware.** This browser exposes neither viewport resizing nor mobile/device emulation. Keyboard zoom attempts left the measured viewport unchanged at 1363 × 936, so they do not count as a narrow test. No cropped desktop screenshot is being represented as mobile evidence. Touch, mobile tooltips, narrow tab access and mobile reset remain untested.

Supplemental downloaded-workbook inspection (not a live narrow test): none of the six published dashboards has an authored device layout. Country uses a range with minimum width 1140 and minimum height 780, maximum 1400 × 1200; the other five use Automatic sizing. An old retained Retail Overview has a device layout but is not one of the six published tabs. These facts indicate that a dedicated phone layout has never been implemented for the published set; its absence is not a regression. Automatic sizing alone is not proof of readable phone reflow.

## Recommendations — not applied

1. Fix clipping in a working copy: allow enough height/reflow for the retail growth label, country/customer boundary notes, cancellation KPI third lines and investigation note. The analytical caveats must remain visible.
2. Format synthetic tooltip percentages consistently with chart labels (at least one decimal; preferably two for QA). Retain mean/median labels and synthetic assumptions.
3. Order tabs Retail → Country → Customer → Cancellation → Synthetic → Improvement and remove trailing punctuation where supported without breaking portfolio links.
4. Implement and test a dedicated narrow layout in a copy: stacked KPIs, readable chart labels, visible caveats and accessible navigation. Country's 1140 minimum requires a deliberate phone alternative.
5. Add filters only if intentionally designed; current static baseline cards/notes must be labelled fixed or converted together. Do not imply unsupported dashboard-wide responsiveness.

Exact next step: review the reproduction branch and resolve the outstanding narrow/touch acceptance in an environment that supports resizing/device emulation. Then, if a correction phase is authorised, use the dated backup/working copy, apply the presentation changes and rerun desktop/narrow/tooltip/selection/reset checks before any separate publication. Live workbook and LinkedIn remain unchanged.
