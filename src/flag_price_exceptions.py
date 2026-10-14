r"""Flag price exceptions; preserve all source values, rows and earlier flags.

Run from portfolio work:
  .\.venv\Scripts\python.exe src\flag_price_exceptions.py

Zero_Price: numeric Price equals zero; transaction classification remains pending.
Negative_Price: numeric Price below zero; not automatically a return.
Bad_Debt_Adjustment: one of the five reviewed source rows, with its reviewed
invoice, stock code B, description Adjust bad debt, quantity 1 and exact price.
Exclude_From_Merchandise_KPIs: True only for those reviewed adjustments.
False is NOT a general eligibility approval; later transaction rules still apply.
Price_Review_Required: zero, nonfinite/unparseable or unclassified negative price.
No filling, sign changes, row deletion, transaction values or KPI calculations.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import platform
import pandas as pd

DEFAULT_RUN = 'description_20260916T220016768319Z'
REVIEWED = {
    'Year 2009-2010!179405': ('A506401', -53594.36),
    'Year 2009-2010!276276': ('A516228', -44031.79),
    'Year 2009-2010!403474': ('A528059', -38925.87),
    'Year 2010-2011!299985': ('A563186', -11062.06),
    'Year 2010-2011!299986': ('A563187', -11062.06),
}
NEW_FLAGS = ['Zero_Price', 'Negative_Price', 'Bad_Debt_Adjustment',
             'Exclude_From_Merchandise_KPIs', 'Price_Review_Required']

def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def classify(frame):
    """Inspect values without rewriting them; unknown cases remain review items."""
    price = pd.to_numeric(frame['Price'], errors='coerce')
    quantity = pd.to_numeric(frame['Quantity'], errors='coerce')
    invalid = price.isna() | price.isin([float('inf'), -float('inf')])
    zero, negative = price.eq(0) & ~invalid, price.lt(0) & ~invalid
    bad = pd.Series(False, index=frame.index)
    for row_id, (invoice, value) in REVIEWED.items():
        bad |= (frame['Source_Row_ID'].eq(row_id) & frame['Invoice'].eq(invoice)
                & frame['StockCode'].eq('B') & frame['Description'].eq('Adjust bad debt')
                & quantity.eq(1) & price.eq(value))
    flags = pd.DataFrame({'Zero_Price': zero, 'Negative_Price': negative,
        'Bad_Debt_Adjustment': bad, 'Exclude_From_Merchandise_KPIs': bad,
        'Price_Review_Required': zero | invalid | (negative & ~bad)})
    category = pd.Series('No price exception', index=frame.index)
    category.loc[zero] = 'Zero price - classification pending'
    category.loc[negative & ~bad] = 'Negative price - classification pending'
    category.loc[bad] = 'Verified bad-debt accounting adjustment'
    category.loc[invalid] = 'Missing, nonnumeric or nonfinite price'
    return flags, category

def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path,
        default=root/'outputs'/DEFAULT_RUN/'transactions_with_description_flag.csv')
    parser.add_argument('--output', type=Path, default=root/'outputs')
    args = parser.parse_args()
    source = args.input.resolve()
    parent_file = source.parent/'description_summary.json'
    if not source.is_file() or not parent_file.is_file():
        raise FileNotFoundError('Expected description CSV and description_summary.json in ' + str(source.parent))
    before, parent_hash = sha256(source), sha256(parent_file)
    parent = json.loads(parent_file.read_text(encoding='utf-8'))
    if before != parent['output_sha256']:
        raise ValueError('Input checksum does not match the description summary')
    print('Reading transactions with both missing-value flags...', flush=True)
    frame = pd.read_csv(source, dtype=str, keep_default_na=False)
    original_columns = frame.columns.tolist()
    required = ['Invoice', 'StockCode', 'Description', 'Quantity', 'Price',
        'Source_Row_ID', 'Source_Period', 'Source_Excel_Row',
        'Missing_Customer_ID', 'Missing_Description']
    if not all(name in frame.columns for name in required):
        raise ValueError('Required source or earlier flag columns are missing')
    if any(name in frame.columns for name in NEW_FLAGS):
        raise ValueError('Input already has price flags; use the previous description output')
    if len(frame) != parent['output_rows'] or not frame['Source_Row_ID'].is_unique:
        raise ValueError('Input row count or provenance failed verification')
    if frame['Source_Row_ID'].str.strip().eq('').any():
        raise ValueError('Blank source row identifier')
    for name, expected in [('Missing_Customer_ID', parent['missing_customer_ids_carried_forward']),
                           ('Missing_Description', parent['missing_descriptions'])]:
        if not frame[name].isin(['True', 'False']).all() or int(frame[name].eq('True').sum()) != expected:
            raise ValueError(f'Previous flag failed verification: {name}')
    flags, category = classify(frame)
    if int(flags['Bad_Debt_Adjustment'].sum()) != len(REVIEWED):
        raise ValueError('The five reviewed bad-debt records do not match; stop for review')
    frame[NEW_FLAGS] = flags
    mask = category.ne('No price exception')
    audit = frame.loc[mask, ['Source_Row_ID', 'Source_Period', 'Source_Excel_Row',
                           'Invoice', 'StockCode', 'Description', 'Quantity', 'Price']].copy()
    audit.rename(columns={'Price': 'Original_Value'}, inplace=True)
    audit.insert(0, 'Issue_ID', 'PRICE_EXCEPTION:' + audit['Source_Row_ID'])
    audit['Issue_Type'] = category.loc[mask]
    audit['Treatment'] = 'Retain unchanged; flag for review; transaction classification pending'
    audit['Reason'] = 'Price alone does not establish a merchandise sale, physical return or error'
    selected = flags.loc[mask, 'Bad_Debt_Adjustment']
    audit.loc[selected, 'Treatment'] = 'Retain unchanged; mark exclusion from merchandise sales/returns KPIs'
    audit.loc[selected, 'Reason'] = 'Reviewed source record explicitly describes a bad-debt accounting adjustment'
    now = datetime.now(timezone.utc)
    if before != sha256(source) or parent_hash != sha256(parent_file):
        raise RuntimeError('Input changed during processing')
    folder = args.output/('price_' + now.strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir(parents=True, exist_ok=False)
    output = folder/'transactions_with_price_flags.csv'
    frame.to_csv(output, index=False)
    audit.to_csv(folder/'price_exception_audit.csv', index=False)
    exported = pd.read_csv(output, dtype=str, keep_default_na=False)
    if not exported[original_columns].equals(frame[original_columns]):
        raise RuntimeError('Original fields or row order changed on export; do not use output')
    for name in NEW_FLAGS:
        if not exported[name].isin(['True', 'False']).all() or not exported[name].eq('True').equals(flags[name]):
            raise RuntimeError('Exported flag failed verification: ' + name)
    if len(audit) != int(mask.sum()) or not audit['Issue_ID'].is_unique:
        raise RuntimeError('Audit reconciliation failed')
    if before != sha256(source) or parent_hash != sha256(parent_file):
        raise RuntimeError('Input changed; do not use output')
    summary = {
        'status': 'Price flags added; all rows retained; KPI filters not yet implemented',
        'run_utc': now.isoformat(), 'input_file': str(source),
        'input_sha256': before, 'input_unchanged': True,
        'parent_description_summary_sha256': parent_hash,
        'original_workbook_sha256_from_parent': parent.get('original_workbook_sha256_from_parent'),
        'output_sha256': sha256(output), 'script_sha256': sha256(Path(__file__)),
        'python_version': platform.python_version(), 'pandas_version': pd.__version__,
        'input_rows': len(frame), 'output_rows': len(exported), 'rows_removed': 0,
        'zero_prices': int(flags['Zero_Price'].sum()),
        'negative_prices': int(flags['Negative_Price'].sum()),
        'verified_bad_debt_adjustments': int(flags['Bad_Debt_Adjustment'].sum()),
        'marked_for_merchandise_kpi_exclusion': int(flags['Exclude_From_Merchandise_KPIs'].sum()),
        'price_review_required': int(flags['Price_Review_Required'].sum()),
        'audit_rows': len(audit), 'exception_categories': category[mask].value_counts().to_dict(),
        'missing_customer_ids_carried_forward': int(frame['Missing_Customer_ID'].eq('True').sum()),
        'missing_descriptions_carried_forward': int(frame['Missing_Description'].eq('True').sum()),
        'previous_flags_unchanged': True,
        'checks': 'Parent hash and counts match; unique provenance; five reviewed records match; original columns/row order and all flags verified through export; audit reconciles; input unchanged',
        'scope_limit': 'No imputation, sign changes or row deletion. Zero-price classification pending. Exclusion=False is not overall eligibility. Future KPI views must apply the exclusion flag.'
    }
    (folder/'price_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(f'Rows retained: {len(frame):,}')
    print(f'Zero prices flagged for review: {summary["zero_prices"]:,}')
    print(f'Negative prices: {summary["negative_prices"]:,}')
    print(f'Verified bad-debt adjustments: {summary["verified_bad_debt_adjustments"]:,}')
    print(f'Price audit entries: {len(audit):,}')
    print('Both previous missing-value flags preserved.')
    print('Rows removed: 0. Original values and previous files unchanged.')
    print(f'Outputs: {folder}')

if __name__ == '__main__':
    main()
