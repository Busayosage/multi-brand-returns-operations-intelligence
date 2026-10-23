"""Add provisional KPI eligibility under documented policy v1.0; preserve all rows.
Requires pandas. Run this script from your existing project virtual environment.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import platform
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
POLICY = '''# KPI definitions — policy v1.0 (provisional analytical scope)

Purpose: measure recorded merchandise sales and cancellation patterns, while
keeping uncertain movements visible. Eligibility is an analytical assumption,
not confirmation that a physical delivery or return occurred.

## Common merchandise rules
Candidate: an existing Product candidate category, or a Numeric-leading code -
not assessed category with a code starting with a digit. The latter is explicitly
promoted only for this provisional analytical policy, not source classification.
No blanket interpretation of Stock_Code_Review_Required=False as eligibility.
Require nonblank description, no exact review-label match from quality review,
strict valid ISO invoice date, finite positive price, finite nonzero integer
quantity, and no prior merchandise-exclusion, price-review or invoice/quantity-
review flag. Other stock categories do not qualify. Original flags stay intact.

Sales require a digits-only invoice and positive quantity. Cancellation entries
require C followed by digits and negative quantity (temporary trim/upper only).
Missing customer ID does not block either. Customer-linked subsets additionally
require a digits-only Customer ID after temporary trimming; this checks format,
not verified customer identity. Within-sheet repetitions remain included under
the existing retention rule; counts must be disclosed and sensitivity assessed.

## KPI dictionary
| KPI | Calculation | Purpose |
|---|---|---|
| Gross merchandise sales value | SUM(Quantity * Price) where Sales_KPI_Eligible | Recorded positive merchandise value |
| Cancellation-marked merchandise value | SUM(ABS(Quantity) * Price) where Cancellation_KPI_Eligible | Recorded cancellation value |
| Net recorded merchandise value | Gross value minus cancellation value | Net movement within this scope |
| Merchandise sales orders | Distinct trimmed Invoice among eligible sales | Sales invoice volume |
| Average merchandise order value | Gross value / eligible sales orders | Average merchandise value per invoice |
| Cancellation-to-sales value ratio | Cancellation value / gross value * 100 | Period movement comparison |
| Identified purchasing customers | Distinct trimmed Customer ID where Customer_Sales_KPI_Eligible | Identifiable purchasing customer count |
| Customer-ID coverage of sales lines | Eligible sales lines with format-valid ID / all eligible sales lines * 100 | Coverage of customer analysis |
| Rows awaiting eligibility review | Count KPI_Eligibility_Status = Review required | Remaining uncertain scope |

Zero denominators produce null (not zero). Aggregate money without rounding
individual lines; round presentation only. Monthly metrics use InvoiceDate month.
December 2011 is partial through 9 December; avoid full-month growth comparisons.
This script creates eligibility only: KPI amounts are calculated in a later step.

Cancellation ratio is not a matched-purchase return rate. Net value is not audited
revenue. No confirmed physical-return rate, processing time, reason or recovery
KPI is supported. Mixed invoices contribute only eligible merchandise lines.
Invoice/customer keys must be checked for reuse/conflicts before order/customer
KPIs are published. No customer identity repair, guessed descriptions or sign
changes. Review labels are a finite observed list, not semantic validation of
all descriptions. Numeric code candidates require this assumption to be disclosed.

## Added fields
- KPI_Policy_Version: reproducible rule version.
- KPI_Merchandise_Candidate: category/code candidate test; not eligibility alone.
- Sales_KPI_Eligible: passes common checks and positive sales invoice rule.
- Cancellation_KPI_Eligible: passes common checks and negative C-invoice rule.
- Customer_ID_Format_Valid: nonblank digits-only identifier; not identity validation.
- Customer_Sales_KPI_Eligible: eligible sale with format-valid customer ID.
- Customer_Cancellation_KPI_Eligible: eligible cancellation with format-valid ID.
- KPI_Eligibility_Status: mutually exclusive sales, cancellation, separate non-
  merchandise category, or unresolved review; supports reconciliation.
- KPI_Eligibility_Reason: all detected exclusion/review reasons separated by |.
  Eligibility reasons do not include missing customer ID, which only limits the
  customer subsets. Preserve all original fields, flags, provenance and row order.
'''


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def classify(df, labels):
    code = df['StockCode'].str.strip()
    cat = df['Stock_Code_Category']
    inv = df['Invoice'].str.strip().str.upper()
    desc = df['Description'].str.strip()
    q = pd.to_numeric(df['Quantity'], errors='coerce')
    p = pd.to_numeric(df['Price'], errors='coerce')
    raw_date = df['InvoiceDate'].str.strip()
    dates = pd.to_datetime(raw_date.where(raw_date.str.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')), format='%Y-%m-%d %H:%M:%S', errors='coerce')
    candidate = cat.eq('Product candidate') | (cat.eq('Numeric-leading code - not assessed') & code.str.match(r'^[0-9]'))
    separate = cat.isin(['Delivery charge', 'Fee', 'Discount', 'Gift voucher', 'Accounting adjustment'])
    sale_shape = inv.str.fullmatch(r'[0-9]+') & q.gt(0)
    cancel_shape = inv.str.fullmatch(r'C[0-9]+') & q.lt(0)
    checks = {
        'Outside candidate merchandise scope': ~candidate,
        'Missing description': desc.eq(''),
        'Description label requires review': desc.str.casefold().isin(labels),
        'Invalid or missing date': dates.isna(),
        'Price not finite and positive': ~(np.isfinite(p) & p.gt(0)),
        'Quantity not finite nonzero integer': ~(np.isfinite(q) & q.ne(0) & q.mod(1).eq(0)),
        'Prior merchandise exclusion': df['Exclude_From_Merchandise_KPIs'].eq('True'),
        'Prior price review': df['Price_Review_Required'].eq('True'),
        'Prior invoice quantity review': df['Invoice_Quantity_Review_Required'].eq('True'),
        'Invoice format or quantity sign requires review': ~(sale_shape | cancel_shape),
    }
    blocked = pd.DataFrame(checks).any(axis=1)
    sale = ~blocked & sale_shape
    cancel = ~blocked & cancel_shape
    customer = df['Customer ID'].str.strip().str.fullmatch(r'[0-9]+')
    status = pd.Series('Review required', index=df.index)
    status.loc[separate] = 'Separate non-merchandise category'
    status.loc[sale] = 'Eligible sales'
    status.loc[cancel] = 'Eligible cancellation'
    reasons = pd.Series('', index=df.index)
    for reason, mask in checks.items():
        reasons.loc[mask] = reasons.loc[mask] + reason + ' | '
    reasons = reasons.str.rstrip(' |')
    reasons.loc[sale | cancel] = 'Passes provisional merchandise policy v1.0'
    return pd.DataFrame({
        'KPI_Policy_Version': '1.0', 'KPI_Merchandise_Candidate': candidate,
        'Sales_KPI_Eligible': sale, 'Cancellation_KPI_Eligible': cancel,
        'Customer_ID_Format_Valid': customer, 'Customer_Sales_KPI_Eligible': sale & customer,
        'Customer_Cancellation_KPI_Eligible': cancel & customer,
        'KPI_Eligibility_Status': status, 'KPI_Eligibility_Reason': reasons,
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'outputs/stock_codes_20260917T004837903105Z/transactions_with_stock_code_categories.csv')
    parser.add_argument('--review', type=Path, default=ROOT / 'outputs/quality_review_20260917T010215552518Z/quality_review_summary.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs')
    args = parser.parse_args()
    source = args.input.resolve()
    parent_path = source.with_name('stock_code_summary.json')
    hashes = {str(x): sha(x) for x in [source, parent_path, args.review]}
    parent = json.loads(parent_path.read_text(encoding='utf-8'))
    review = json.loads(args.review.read_text(encoding='utf-8'))
    need(hashes[str(source)] == parent['output_sha256'] == review['input_sha256'], 'Input/parent/quality-review checksum mismatch.')
    print('Reading reviewed transactions...')
    df = pd.read_csv(source, dtype=str, keep_default_na=False)
    need(len(df) == parent['output_rows'] == review['input_rows'], 'Row counts mismatch.')
    need(df['Source_Row_ID'].is_unique and df['Source_Row_ID'].str.strip().ne('').all(), 'Invalid source IDs.')
    for c, n in parent['prior_flag_counts'].items():
        need(df[c].isin(['True', 'False']).all() and int(df[c].eq('True').sum()) == n, f'Flag mismatch: {c}')
    added = classify(df, review['rules']['description_review_labels'])
    need(not set(added.columns) & set(df.columns), 'KPI columns already exist: use the stock-code input.')
    need(not (added['Sales_KPI_Eligible'] & added['Cancellation_KPI_Eligible']).any(), 'Eligibility overlap.')
    counts = added['KPI_Eligibility_Status'].value_counts().to_dict()
    need(sum(counts.values()) == len(df), 'Status counts mismatch.')
    run = datetime.now(timezone.utc)
    out = args.output.resolve() / ('kpi_eligibility_' + run.strftime('%Y%m%dT%H%M%S%fZ'))
    out.mkdir(parents=True, exist_ok=False)
    result = pd.concat([df, added], axis=1)
    output = out / 'transactions_with_kpi_eligibility.csv'
    result.to_csv(output, index=False)
    readback = pd.read_csv(output, dtype=str, keep_default_na=False)
    pd.testing.assert_frame_equal(readback[df.columns], df)
    pd.testing.assert_frame_equal(readback[added.columns], added.astype(str))
    grouped = added.groupby(['KPI_Eligibility_Status', 'KPI_Eligibility_Reason']).size().reset_index(name='Rows')
    grouped.to_csv(out / 'eligibility_reason_summary.csv', index=False)
    (out / 'KPI_DEFINITIONS_v1.md').write_text(POLICY, encoding='utf-8')
    need(all(sha(Path(path)) == value for path, value in hashes.items()), 'An input changed during processing.')
    summary = {
        'status': 'Provisional policy v1.0 applied; KPI values not yet calculated',
        'run_utc': run.isoformat(), 'input_file': str(source), 'input_sha256': hashes[str(source)],
        'parent_hashes': hashes, 'input_rows': len(df), 'output_rows': len(result), 'rows_removed': 0,
        'original_workbook_sha256_from_parent': parent['original_workbook_sha256_from_parent'],
        'output_sha256': sha(output), 'script_sha256': sha(Path(__file__)),
        'policy_sha256': sha(out / 'KPI_DEFINITIONS_v1.md'),
        'reason_summary_sha256': sha(out / 'eligibility_reason_summary.csv'),
        'policy_version': '1.0', 'python_version': platform.python_version(), 'pandas_version': pd.__version__,
        'status_counts': counts,
        'eligibility_counts': {c: int(added[c].sum()) for c in added.select_dtypes(include='bool')},
        'eligible_sales_within_sheet_repetition_rows': int((added['Sales_KPI_Eligible'] & df['Within_Sheet_Repetition'].eq('True')).sum()),
        'eligible_cancellation_within_sheet_repetition_rows': int((added['Cancellation_KPI_Eligible'] & df['Within_Sheet_Repetition'].eq('True')).sum()),
        'checks': 'Input checksums and flags reconcile; unique provenance; disjoint sales/cancellation; all rows reconciled; full CSV readback preserves every original field/flag/order; inputs unchanged.',
        'scope_limit': 'Provisional numeric-code merchandise assumption. No physical-return confirmation or source edits. Prior stock-review flags remain unchanged. See KPI_DEFINITIONS_v1.md before publishing any KPI.',
    }
    (out / 'kpi_eligibility_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(f'Rows retained: {len(df):,}')
    for label, count in counts.items():
        print(f'{label}: {count:,}')
    print(f'Customer-linked eligible sales lines: {int(added["Customer_Sales_KPI_Eligible"].sum()):,}')
    print('Rows removed: 0. All original columns and prior flags preserved.')
    print('Policy is provisional; KPI amounts are not yet calculated.')
    print(f'Outputs: {out}')


if __name__ == '__main__':
    main()
