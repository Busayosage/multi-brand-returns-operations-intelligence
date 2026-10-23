"""Review invoice identity and release order KPIs under a documented counting rule.
Keep calculate_kpis.py in the same src folder. No source data is changed.
"""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import argparse
import json
import pandas as pd
from calculate_kpis import sha, need, metrics

ROOT=Path(__file__).resolve().parents[1]
RULE='''# Invoice counting rule v1.1

Merchandise eligibility stays at policy v1.0. Count each trimmed, upper-case
invoice number once among eligible sales lines. A timestamp difference does not
split an invoice when all its rows fall on one calendar day, the total timestamp
span is at most 10 minutes, and there is at most one distinct nonblank customer
and one distinct nonblank country. All timestamps must parse successfully.
The observed 83 exceptions span 1–9 minutes. The 10-minute limit is an analytical
review threshold for this dataset, not a verified source-system guarantee.

Missing customer ID does not invalidate an invoice count; it still prevents
customer-linked eligibility for those rows. No identity is filled or invented.
Conflicting customers/countries, multiple days, invalid dates or spans above
10 minutes keep affected order counts and AOV withheld. Audit all invoices,
including ineligible and non-merchandise lines. Calendar date alone is never
used to merge different invoice numbers. No composite order key is invented.

This is an invoice-based order proxy, not proof of separate physical orders.
Source-system documentation would be required to confirm the underlying cause
of the minute-level timestamp differences. Do not describe them as proven
split shipments, separate purchases or corrections.

Updated overall/monthly KPIs use the same eligible lines and exact Decimal
amounts as the previous run. Only order-count/AOV release rules change. Prior
reports remain intact. Repetition sensitivity stays in the previous KPI folder.
Customer counts and monthly distinct counts are non-additive. December 2011 is
partial through 9 December. Cancellation values are not confirmed physical
returns. See upstream KPI_DEFINITIONS_v1.md and READ_KPI_REPORTS.md for scope.
'''


def profile(df):
    tmp=pd.DataFrame({'Invoice_Key':df['Invoice'].str.strip().str.upper(),
        'Customer':df['Customer ID'].str.strip().replace('',pd.NA),
        'Country':df['Country'].str.strip().replace('',pd.NA),
        'Timestamp':pd.to_datetime(df['InvoiceDate'],format='%Y-%m-%d %H:%M:%S',errors='coerce')})
    tmp['Day']=tmp.Timestamp.dt.strftime('%Y-%m-%d')
    tmp['Invalid_Date']=tmp.Timestamp.isna()
    p=tmp.loc[tmp.Invoice_Key.ne('')].groupby('Invoice_Key').agg(
        Rows=('Invoice_Key','size'),Customers=('Customer','nunique'),Countries=('Country','nunique'),
        Timestamps=('Timestamp','nunique'),Days=('Day','nunique'),
        First_Timestamp=('Timestamp','min'),Last_Timestamp=('Timestamp','max'),Invalid_Dates=('Invalid_Date','sum'))
    p['Span_Minutes']=(p.Last_Timestamp-p.First_Timestamp).dt.total_seconds()/60
    p['Order_Key_Review_Required']=(p.Customers.gt(1)|p.Countries.gt(1)|p.Days.ne(1)|p.Invalid_Dates.gt(0)|p.Span_Minutes.gt(10))
    p['Timestamp_Variation_Accepted']=p.Timestamps.gt(1)&~p.Order_Key_Review_Required
    return p


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'outputs/kpi_eligibility_20260917T012349887393Z/transactions_with_kpi_eligibility.csv')
    parser.add_argument('--prior-kpis',type=Path,default=ROOT/'outputs/kpis_20260917T013533989561Z')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs')
    args=parser.parse_args()
    source=args.input.resolve(); parent_path=source.with_name('kpi_eligibility_summary.json')
    prior_path=args.prior_kpis/'kpi_summary.json'; audit_path=args.prior_kpis/'invoice_consistency_audit.csv'
    paths=[source,parent_path,prior_path,audit_path,Path(__file__).with_name('calculate_kpis.py')]
    hashes={str(p):sha(p) for p in paths}
    parent=json.loads(parent_path.read_text(encoding='utf-8')); prior=json.loads(prior_path.read_text(encoding='utf-8'))
    need(parent['output_sha256']==hashes[str(source)],'Input hash mismatch.')
    # Prior report may contain a Windows or Linux absolute path; compare its value.
    need(prior['input_hashes'][prior['input_file']]==hashes[str(source)],'Prior KPI run used a different dataset.')
    need(prior['output_hashes']['invoice_consistency_audit.csv']==hashes[str(audit_path)],'Audit checksum mismatch.')
    print('Reviewing invoice keys across all retained rows...')
    df=pd.read_csv(source,dtype=str,keep_default_na=False)
    need(len(df)==parent['output_rows'] and df.Source_Row_ID.is_unique,'Row/provenance mismatch.')
    for c,n in parent['eligibility_counts'].items():
        need(df[c].isin(['True','False']).all() and int(df[c].eq('True').sum())==n,f'Flag mismatch: {c}')
    p=profile(df); old=pd.read_csv(audit_path,dtype=str,keep_default_na=False)
    need(set(old.Invoice_Key)<=set(p.index),'Prior audit key missing.')
    old_details=p.loc[old.Invoice_Key].reset_index()
    bad=set(p.index[p.Order_Key_Review_Required]);bad_customer=set(p.index[p.Customers.gt(1)])
    work=df.loc[df.Sales_KPI_Eligible.eq('True')|df.Cancellation_KPI_Eligible.eq('True')].copy()
    work['_invoice']=work.Invoice.str.strip().str.upper();work['_customer']=work['Customer ID'].str.strip()
    dates=pd.to_datetime(work.InvoiceDate,format='%Y-%m-%d %H:%M:%S',errors='raise')
    work['_month']=dates.dt.strftime('%Y-%m')
    work['_value']=[Decimal(q)*Decimal(price) for q,price in zip(work.Quantity,work.Price)]
    overall=metrics(work,bad,bad_customer)
    for c in ['Gross_Value_Exact','Cancellation_Value_Exact','Sales_Lines','Cancellation_Lines','Identified_Purchasing_Customers']:
        need(overall[c]==prior['overall'][c],f'Unexpected baseline change: {c}')
    monthly=[]
    for month in pd.period_range(pd.Timestamp(prior['source_date_min']).to_period('M'),pd.Timestamp(prior['source_date_max']).to_period('M'),freq='M'):
        label=str(month)
        monthly.append({'Month':label,**metrics(work.loc[work['_month'].eq(label)],bad,bad_customer),
            'Coverage':'Partial boundary month' if label=='2011-12' else 'Within observed date span'})
    for c in ['Gross_Value_Exact','Cancellation_Value_Exact']:
        need(sum((Decimal(r[c]) for r in monthly),Decimal(0))==Decimal(overall[c]),'Monthly value mismatch.')
    if not work['_invoice'].isin(bad).any():
        need(sum(r['Sales_Orders'] for r in monthly)==overall['Sales_Orders'],'Released monthly order counts do not reconcile.')
    out=args.output.resolve()/('invoice_review_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir(parents=True,exist_ok=False)
    reports={'reviewed_invoice_keys.csv':old_details,'remaining_invoice_key_review.csv':p.loc[p.Order_Key_Review_Required].reset_index(),
        'kpi_overall_reviewed.csv':pd.DataFrame([overall]),'kpi_monthly_reviewed.csv':pd.DataFrame(monthly)}
    output_hashes={}
    for name,frame in reports.items():
        path=out/name
        # Explicit text representation also makes report readback deterministic.
        expected=frame.fillna('').astype(str)
        expected.to_csv(path,index=False)
        pd.testing.assert_frame_equal(pd.read_csv(path,dtype=str,keep_default_na=False),expected)
        output_hashes[name]=sha(path)
    (out/'INVOICE_COUNTING_RULE_v1_1.md').write_text(RULE,encoding='utf-8')
    output_hashes['INVOICE_COUNTING_RULE_v1_1.md']=sha(out/'INVOICE_COUNTING_RULE_v1_1.md')
    need(all(sha(Path(p))==v for p,v in hashes.items()),'Input changed during review.')
    summary={'status':'Invoice-counting rule v1.1 applied; merchandise policy v1.0 unchanged',
        'input_hashes':hashes,'output_hashes':output_hashes,'script_sha256':sha(Path(__file__)),
        'input_rows':len(df),'rows_removed':0,'previous_flagged_invoice_keys':len(old),
        'accepted_timestamp_variations':int(old_details.Timestamp_Variation_Accepted.sum()),
        'remaining_invoice_keys_requiring_review':len(bad),'overall':overall,
        'checks':'Parent/prior report checksums, eligibility counts, invoice coverage, monetary invariance, monthly reconciliation, report readback and unchanged inputs verified.'}
    (out/'invoice_review_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(f'Previously flagged invoice keys: {len(old)}')
    print(f'Accepted same-day timestamp variations: {summary["accepted_timestamp_variations"]}')
    print(f'Remaining invoice keys requiring review: {len(bad)}')
    print(f'Sales orders (invoice proxy): {overall["Sales_Orders"]}')
    print(f'Average merchandise order value: {overall["Average_Merchandise_Order_Value"]}')
    print('Money totals unchanged. All source rows and prior outputs preserved.')
    print(f'Outputs: {out}')

if __name__=='__main__':main()
