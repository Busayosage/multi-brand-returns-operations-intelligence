# Part 2 — Cancellation Exceptions & Synthetic Logistics Intelligence

**Independent portfolio | evidence review completed 16 October 2026 | Python + SQLite**

## The question

Cancellation-marked merchandise value grew while the number of eligible cancellation lines fell. Does that mean an actual deterioration in warehouse returns or product quality? **No.** First examine transaction-level outliers, and only claim logistics outcomes when real shipment records exist.

## Source, policy and verification

- Public [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii), analysed from the recovered local `retail_analytics.db` (database intentionally excluded from GitHub).
- Read-only SQLite `PRAGMA quick_check`: `ok`. Source and analysis tables both contain **1,044,848** retained rows, after previously documented overlap reconciliation.
- Historical Work checkpoint verified all 28 KPI scopes against its saved report; **this Part 2 run separately re-executed the cancellation queries and assertions** against the recovered SQLite database.
- Comparable windows: **January–November 2010** and **January–November 2011**; December 2011 is incomplete.
- Policy: provisional merchandise KPI eligibility. Values stored in integer **GBP thousandths** and rounded only for reporting. C-prefixed invoices with eligible negative quantities are cancellation-marked entries, **not proof of physical returns**.
- Database SHA-256: `d601c1c9630669c2c07847e885e5622cef6170468f6611728d366e1449416604`.

## Measured cancellation findings (real source)

| Metric | Jan–Nov 2010 | Jan–Nov 2011 | Direction |
|---|---:|---:|---|
| Cancellation-marked value | £221,407.48 | £286,989.56 | +29.62% |
| Eligible cancellation lines | 8,286 | 7,658 | −7.58% |
| Gross merchandise value | £8,628,418.42 | £8,878,008.02 | +2.89% |
| Cancellation-marked value / gross merchandise value | 2.57% | 3.23% | +0.66 percentage points (rounded figures) |

**The exception:** Product code `23166` (`MEDIUM CERAMIC TOP STORAGE JAR`) accounts for **£77,479.64**, roughly **27.00%** of the total 2011 cancellation-marked value, across **10** eligible cancellation lines. One cancellation line contributes **£77,183.60** of that product total.

Two preserved source rows, `Year 2010-2011!61621` and `Year 2010-2011!61626`, record **+74,215** units and **−74,215** units respectively, both at **£1.04**, to the same recorded customer and product, **16 minutes apart** on 18 January 2011. Each direction is **£77,183.60**. The cancellation leg alone is **26.89%** of 2011 cancellation value. This is a **candidate offsetting reversal**, not confirmation of physical returns, defect, error, fraud, refund or causal explanation.

### Sensitivity, not a corrected KPI

| 2011 Jan–Nov scenario | Gross value | Cancellation-marked value | Net recorded merchandise value | Cancellation-value ratio |
|---|---:|---:|---:|---:|
| All eligible records (**headline**) | £8,878,008.02 | £286,989.56 | £8,591,018.46 | **3.23%** |
| Exclude **both** reviewed offsetting rows (**sensitivity only**) | £8,800,824.42 | £209,805.96 | £8,591,018.46 | **2.38%** |

The 0.85 percentage-point change illustrates outlier sensitivity; **retain 3.23% as the original KPI**. Do not discard the rows, rename 2.38% a corrected rate, or infer that physical returns improved. Comparing an adjusted 2011 rate with an unadjusted 2010 rate would be methodologically inconsistent.

## Separate, openly fictional logistics prototype

The public retail source contains **no carrier, warehouse, package tracking, event scan, return reason, SLA or processing-cost facts**. A separate Python simulation therefore generates **5,000 fictional cases**, prefixed `SIM-`, with `provenance=SYNTHETIC_ONLY`. There is **no shared invoice, customer, order or row ID** linking them to the retail transactions.

Configured demonstration assumptions: three anonymous carriers, three fictional warehouses, request → handover → warehouse receipt → inspection → resolution event sequence; seven-calendar-day SLA; deliberately varied simulated transport and processing times, including a programmed Friday–Sunday transit uplift. This intentionally produces artificial performance differences.

For seed `2026`, the simulation produced **96.72%** of cases inside the configured SLA, a **5.07-day** median cycle time and **6.44-day** 90th-percentile cycle time. Carrier C's **90.94%** versus Carrier A's **99.62%** on-time outcomes arise from assumptions inside the generator, **not actual carrier results**. The same is true of hub and weekday comparisons. Modelled processing costs are fictional, not measured savings.

### Reproduction and checks

```bash
# Place your separately retained original retail_analytics.db in database/ locally.
python src/part2_returns_intelligence.py \
  --db database/retail_analytics.db \
  --output-dir outputs/part2 --count 5000 --seed 2026

# Run the full evidence checks (read-only DB test + synthetic tests)
PART2_DB=database/retail_analytics.db python -m unittest discover -s tests -p 'test_part2*.py' -v
```

Results: `outputs/part2/part2_results.json` and `outputs/part2/synthetic_returns_cases.csv`. The raw source database and generated case-level CSV are not committed. SQL review queries are in `sql/17_cancellation_exception_intelligence.sql`.

**Five unit tests passed**, including real database aggregate/pair reconciliation, deterministic simulation, distinct synthetic IDs, timestamp ordering and refusal of mismarked/invalid records. The local test run does **not** demonstrate a production ETL deployment or an actual logistics improvement.

## Operations decisions and Part 3 handoff

1. **Triage high-value cancellation exceptions** before treating a value-based ratio as evidence of widespread return problems. Preserve an auditable link to exact source rows.
2. Request original-order references and cancellation reasons to distinguish same-day reversal, credit adjustments and genuinely shipped returns. The public source alone cannot resolve this.
3. If real return-scan events later become available, add shipment IDs, event completeness, carrier/hub SLA definitions and operational costs; then compare actual lanes with controls and sample sizes.
4. In Part 3, build the Pareto/control approach and measurable improvement hypotheses. No observed savings, live carrier failure or realised intervention is claimed here.

**Boundary:** public transaction findings = observed; fictional logistics demonstrations = modelled; causal or operational improvements = hypotheses awaiting evidence.
