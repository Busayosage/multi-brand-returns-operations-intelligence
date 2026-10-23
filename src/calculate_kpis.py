"""Calculate provisional policy-v1 KPIs without altering transactions.
Requires pandas. Reports only; repeated-row alternative is sensitivity, not cleaning.
"""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import argparse
import hashlib
import json
import platform
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ZERO = Decimal('0')
FIELDS = ['Invoice', 'StockCode', 'Description', 'Quantity', 'InvoiceDate', 'Price', 'Customer ID', 'Country']


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def display(value):
    return None if value is None else str(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def ratio(n, d, factor=1):
    return None if not d else display(Decimal(n) / Decimal(d) * factor)


def metrics(frame, bad_orders, bad_customers):
    sales = frame.loc[frame['Sales_KPI_Eligible'].eq('True')]
    cancels = frame.loc[frame['Cancellation_KPI_Eligible'].eq('True')]
    gross = sum(sales['_value'], ZERO)
    cancelled = -sum(cancels['_value'], ZERO)
    raw_orders = int(sales['_invoice'].nunique())
    order_hold = bool(sales['_invoice'].isin(bad_orders).any())
    customer_hold = bool(sales['_invoice'].isin(bad_customers).any())
    linked = sales.loc[sales['Customer_Sales_KPI_Eligible'].eq('True')]
    return {
        'Sales_Lines': len(sales), 'Cancellation_Lines': len(cancels),
        'Gross_Merchandise_Value': display(gross),
        'Cancellation_Marked_Value': display(cancelled),
        'Net_Recorded_Merchandise_Value': display(gross-cancelled),
        'Gross_Value_Exact': str(gross), 'Cancellation_Value_Exact': str(cancelled),
        'Sales_Orders': None if order_hold else raw_orders,
        'Distinct_Sales_Invoice_Keys_Diagnostic': raw_orders,
        'Average_Merchandise_Order_Value': None if order_hold else ratio(gross, raw_orders),
        'Cancellation_To_Sales_Value_Pct': ratio(cancelled, gross, 100),
        'Identified_Purchasing_Customers': None if customer_hold else int(linked['_customer'].nunique()),
        'Distinct_Sales_Customer_IDs_Diagnostic': int(linked['_customer'].nunique()),
        'Customer_Linked_Sales_Lines': len(linked),
        'Customer_ID_Coverage_Sales_Lines_Pct': ratio(len(linked), len(sales), 100),
        'Order_KPI_Status': 'Held: invoice consistency review' if order_hold else 'Provisional',
        'Customer_KPI_Status': 'Held: conflicting invoice customer IDs' if customer_hold else 'Provisional',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'outputs/kpi_eligibility_20260917T012349887393Z/transactions_with_kpi_eligibility.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs')
    args = parser.parse_args()
    source = args.input.resolve()
    parent_path = source.with_name('kpi_eligibility_summary.json')
    policy_path = source.with_name('KPI_DEFINITIONS_v1.md')
    hashes = {str(p): sha(p) for p in [source, parent_path, policy_path]}
    parent = json.loads(parent_path.read_text(encoding='utf-8'))
    need(parent['output_sha256'] == hashes[str(source)], 'Input checksum mismatch.')
    need(parent['policy_sha256'] == hashes[str(policy_path)], 'Policy document checksum mismatch.')
    need(parent['policy_version'] == '1.0', 'Only policy v1.0 is supported.')
    print('Reading KPI-eligible transactions...')
    df = pd.read_csv(source, dtype=str, keep_default_na=False)
    need(len(df) == parent['output_rows'], 'Row count mismatch.')
    need(df['Source_Row_ID'].is_unique and df['Source_Row_ID'].str.strip().ne('').all(), 'Invalid provenance.')
    need(df['KPI_Eligibility_Status'].value_counts().to_dict() == parent['status_counts'], 'Status mismatch.')
    for c,n in parent['eligibility_counts'].items():
        need(df[c].isin(['True','False']).all() and int(df[c].eq('True').sum()) == n, f'Flag mismatch: {c}')
    sale = df['Sales_KPI_Eligible'].eq('True')
    cancel = df['Cancellation_KPI_Eligible'].eq('True')
    need(not (sale & cancel).any(), 'Overlapping sales/cancellation flags.')
    dates = pd.to_datetime(df['InvoiceDate'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    need(dates.loc[sale|cancel].notna().all(), 'Eligible rows contain invalid dates.')
    df['_invoice'] = df['Invoice'].str.strip().str.upper()
    df['_customer'] = df['Customer ID'].str.strip()
    df['_date'] = df['InvoiceDate'].str.strip()
    df['_country'] = df['Country'].str.strip()
    # Inspect every line of each invoice, including non-merchandise lines.
    key_frame = df.loc[df['_invoice'].ne(''), ['_invoice','_customer','_date','_country']].copy()
    for c in ['_customer','_date','_country']:
        key_frame[c] = key_frame[c].replace('', pd.NA)
    keys = key_frame.groupby('_invoice').nunique(dropna=True).rename(columns={
        '_customer':'Distinct_Nonblank_Customers','_date':'Distinct_Timestamps','_country':'Distinct_Nonblank_Countries'})
    conflicts = keys.loc[keys.gt(1).any(axis=1)].reset_index().rename(columns={'_invoice':'Invoice_Key'})
    bad_orders = set(conflicts['Invoice_Key'])
    bad_customers = set(conflicts.loc[conflicts['Distinct_Nonblank_Customers'].gt(1),'Invoice_Key'])
    work = df.loc[sale|cancel].copy()
    # Decimal preserves the source decimal precision; no per-line rounding.
    values = []
    for q,p in zip(work['Quantity'],work['Price']):
        quantity, price = Decimal(q), Decimal(p)
        need(quantity.is_finite() and price.is_finite() and price>0 and quantity!=0, 'Invalid eligible numeric value.')
        values.append(quantity*price)
    work['_value'] = values
    work['_month'] = dates.loc[work.index].dt.strftime('%Y-%m')
    need(all(v>0 for v in work.loc[work['Sales_KPI_Eligible'].eq('True'),'_value']), 'Sales sign mismatch.')
    need(all(v<0 for v in work.loc[work['Cancellation_KPI_Eligible'].eq('True'),'_value']), 'Cancellation sign mismatch.')
    overall = metrics(work,bad_orders,bad_customers)
    first,last = dates.min(),dates.max()
    monthly = []
    for month in pd.period_range(first.to_period('M'),last.to_period('M'),freq='M'):
        label = str(month)
        partial = (month == first.to_period('M') and first.day != 1) or (month == last.to_period('M') and last.day != month.days_in_month)
        monthly.append({'Month':label,'Coverage':'Partial boundary month' if partial else 'Within observed date span', **metrics(work.loc[work['_month'].eq(label)],bad_orders,bad_customers)})
    for field in ['Gross_Value_Exact','Cancellation_Value_Exact']:
        need(sum((Decimal(r[field]) for r in monthly),ZERO)==Decimal(overall[field]), 'Monthly money reconciliation failed.')
    for field in ['Sales_Lines','Cancellation_Lines','Customer_Linked_Sales_Lines']:
        need(sum(r[field] for r in monthly)==overall[field], 'Monthly line count reconciliation failed.')
    # Original eight source values, exact exported strings: retain first occurrence
    # across the combined analytical data only for an alternative scenario.
    repeated = work.duplicated(FIELDS, keep='first')
    alternative = metrics(work.loc[~repeated],bad_orders,bad_customers)
    sensitivity = [ {'Scenario':'Baseline: all retained rows',**overall},
                    {'Scenario':'Sensitivity only: one per exact eight-field combination',**alternative} ]
    run = datetime.now(timezone.utc)
    out = args.output.resolve()/('kpis_'+run.strftime('%Y%m%dT%H%M%S%fZ'))
    out.mkdir(parents=True,exist_ok=False)
    reports = {'kpi_overall.csv':pd.DataFrame([overall]), 'kpi_monthly.csv':pd.DataFrame(monthly),
               'invoice_consistency_audit.csv':conflicts, 'repetition_sensitivity.csv':pd.DataFrame(sensitivity),
               'eligibility_status_counts.csv':pd.DataFrame(list(parent['status_counts'].items()),columns=['Status','Rows'])}
    output_hashes = {}
    for name,frame in reports.items():
        path=out/name
        frame.to_csv(path,index=False)
        loaded=pd.read_csv(path,dtype=str,keep_default_na=False)
        expected=frame.fillna('').astype(str)
        pd.testing.assert_frame_equal(loaded,expected,check_dtype=False)
        output_hashes[name]=sha(path)
    notes='''# Reading these KPI reports
Policy v1.0 remains provisional. Money follows the source Price unit (GBP in the
source dataset); no currency conversion. Exact decimal values are included for
reconciliation. Display values round to two decimals with half-up rounding.

Invoice consistency checks use all source lines per trimmed, upper-case invoice:
more than one nonblank customer, country or timestamp is a review signal, not
proof of an error. Affected order counts/AOV are withheld (blank). Customer counts
are withheld where invoices have conflicting nonblank customer IDs. Diagnostic
distinct-key counts remain available and must not be presented as validated KPIs.
A single customer ID across different countries is not automatically an error;
these data do not validate real-world identity. IDs retain leading zeros.

Monthly customers must not be summed to obtain overall customers. Invoice counts
also need not be additive across months. Ratios/AOV must be recomputed from their
numerators and denominators, never averaged. Zero denominator means blank/null.
December 2011 ends on 9 December and is partial. Other months are within the observed
date span, not guaranteed complete. No growth metrics or extrapolation are applied.

Baseline retains repetitions. The sensitivity scenario retains one of each exact
eight-source-field combination among eligible rows, across the combined dataset;
it is not a corrected dataset and does not establish that repetitions are errors.
This can differ from historic within-sheet flags. All input rows remain unchanged.

Cancellation value is the magnitude of eligible negative C-invoice lines; no
original-sale matching or confirmed physical return is inferred. Net movement
is not audited revenue. Non-merchandise/review rows are outside monetary scope;
missing customer IDs remain in eligible sales/cancellation amounts. See upstream
KPI_DEFINITIONS_v1.md for candidate-merchandise assumptions and field definitions.
'''
    (out/'READ_KPI_REPORTS.md').write_text(notes,encoding='utf-8')
    output_hashes['READ_KPI_REPORTS.md']=sha(out/'READ_KPI_REPORTS.md')
    need(all(sha(Path(p))==v for p,v in hashes.items()),'An input changed during calculation.')
    summary={'status':'Provisional KPI reports calculated; inspect invoice audit before publication',
        'run_utc':run.isoformat(),'input_file':str(source),'input_hashes':hashes,'input_rows':len(df),
        'rows_removed':0,'input_unchanged':True,'policy_version':'1.0','overall':overall,
        'invoice_keys_requiring_review':len(conflicts),'eligible_invoice_keys_requiring_review':len(set(work['_invoice'])&bad_orders),
        'sensitivity_excess_eligible_rows':int(repeated.sum()),
        'sensitivity_gross_value_difference':display(Decimal(overall['Gross_Value_Exact'])-Decimal(alternative['Gross_Value_Exact'])),
        'sensitivity_cancellation_value_difference':display(Decimal(overall['Cancellation_Value_Exact'])-Decimal(alternative['Cancellation_Value_Exact'])),
        'source_date_min':str(first),'source_date_max':str(last),'monthly_periods':len(monthly),
        'original_workbook_sha256_from_parent':parent['original_workbook_sha256_from_parent'],
        'script_sha256':sha(Path(__file__)),'python_version':platform.python_version(),'pandas_version':pd.__version__,
        'output_hashes':output_hashes,'checks':'Input checksum, policy hash, provenance, eligibility counts/signs, monthly exact money and line reconciliation, report readback and unchanged inputs verified.'}
    (out/'kpi_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    for key in ['Gross_Merchandise_Value','Cancellation_Marked_Value','Net_Recorded_Merchandise_Value','Sales_Orders','Average_Merchandise_Order_Value','Identified_Purchasing_Customers']:
        print(f'{key}: {overall[key]}')
    print(f'Invoice keys requiring consistency review: {len(conflicts):,}')
    print(f'Eligible repeated excess rows (sensitivity only): {int(repeated.sum()):,}')
    print('All source rows preserved. Monthly and repetition-sensitivity reports created.')
    print(f'Outputs: {out}')

if __name__=='__main__':
    main()
