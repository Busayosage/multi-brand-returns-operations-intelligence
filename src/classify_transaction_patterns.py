r"""Classify observed invoice/quantity patterns, not confirmed physical returns.

Run from portfolio work:
  .\.venv\Scripts\python.exe src\classify_transaction_patterns.py

Preserve every input column, row and flag. Add Is_Cancellation,
Transaction_Type and Invoice_Quantity_Review_Required. Other positive
movements remain unclassified; no sales/return eligibility is inferred.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import platform
import pandas as pd

DEFAULT_RUN = 'price_20260916T231154907959Z'
ADDED = ['Is_Cancellation', 'Transaction_Type', 'Invoice_Quantity_Review_Required']
PRIOR_FLAGS = ['Missing_Customer_ID', 'Missing_Description', 'Zero_Price',
    'Negative_Price', 'Bad_Debt_Adjustment', 'Exclude_From_Merchandise_KPIs', 'Price_Review_Required']

def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def classify(frame):
    q = pd.to_numeric(frame['Quantity'], errors='coerce')
    c = frame['Invoice'].str.upper().str.startswith('C')
    bad = frame['Bad_Debt_Adjustment'].eq('True')
    missing_invoice = frame['Invoice'].str.strip().eq('')
    invalid = q.isna() | q.isin([float('inf'), -float('inf')])
    noninteger = ~invalid & q.mod(1).ne(0)
    types = pd.Series('Other movement - not yet classified', index=frame.index)
    types.loc[c & q.lt(0)] = 'Cancellation-marked negative line'
    types.loc[c & q.gt(0)] = 'Cancellation quantity exception'
    types.loc[~c & q.lt(0)] = 'Unclassified negative movement'
    types.loc[q.eq(0)] = 'Zero quantity - review'
    types.loc[noninteger] = 'Noninteger quantity - review'
    types.loc[invalid] = 'Invalid quantity - review'
    types.loc[missing_invoice] = 'Missing invoice - review'
    # Verified accounting classification takes precedence over movement signs.
    types.loc[bad] = 'Accounting adjustment'
    review = ((c & q.gt(0)) | (~c & q.lt(0)) | q.eq(0)
              | invalid | noninteger | missing_invoice)
    return pd.DataFrame({'Is_Cancellation': c, 'Transaction_Type': types,
                         'Invoice_Quantity_Review_Required': review})

def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path,
        default=root/'outputs'/DEFAULT_RUN/'transactions_with_price_flags.csv')
    parser.add_argument('--output', type=Path, default=root/'outputs')
    args = parser.parse_args()
    source = args.input.resolve()
    parent_file = source.parent/'price_summary.json'
    if not source.is_file() or not parent_file.is_file():
        raise FileNotFoundError('Expected price CSV and price_summary.json in ' + str(source.parent))
    before, parent_hash = sha256(source), sha256(parent_file)
    parent = json.loads(parent_file.read_text(encoding='utf-8'))
    if before != parent['output_sha256']:
        raise ValueError('Input checksum differs from price summary')
    print('Reading price-flagged transactions...', flush=True)
    frame = pd.read_csv(source, dtype=str, keep_default_na=False)
    original_columns = frame.columns.tolist()
    required = ['Invoice', 'Quantity', 'Price', 'StockCode', 'Description',
                'Source_Row_ID', 'Source_Period', 'Source_Excel_Row'] + PRIOR_FLAGS
    if not all(name in frame.columns for name in required):
        raise ValueError('Required columns missing')
    if any(name in frame.columns for name in ADDED):
        raise ValueError('Input already contains classification columns; select the previous price output')
    if len(frame) != parent['output_rows'] or not frame['Source_Row_ID'].is_unique:
        raise ValueError('Input count/provenance mismatch')
    if frame['Source_Row_ID'].str.strip().eq('').any():
        raise ValueError('Blank source row ID')
    for name in PRIOR_FLAGS:
        if not frame[name].isin(['True', 'False']).all():
            raise ValueError('Unexpected prior flag values: ' + name)
    mapping = {'Missing_Customer_ID':'missing_customer_ids_carried_forward',
        'Missing_Description':'missing_descriptions_carried_forward', 'Zero_Price':'zero_prices',
        'Negative_Price':'negative_prices', 'Bad_Debt_Adjustment':'verified_bad_debt_adjustments',
        'Exclude_From_Merchandise_KPIs':'marked_for_merchandise_kpi_exclusion',
        'Price_Review_Required':'price_review_required'}
    prior_counts = {name: int(frame[name].eq('True').sum()) for name in PRIOR_FLAGS}
    if any(prior_counts[name] != parent[key] for name, key in mapping.items()):
        raise ValueError('Previous flag counts do not reconcile with parent summary')
    added = classify(frame)
    frame[ADDED] = added
    # Audit unresolved sign/data exceptions, plus the preserved accounting class.
    # Cancellation-marked negative lines remain in the main dataset and summary.
    mask = added['Invoice_Quantity_Review_Required'] | frame['Bad_Debt_Adjustment'].eq('True')
    audit = frame.loc[mask, ['Source_Row_ID', 'Source_Period', 'Source_Excel_Row',
        'Invoice', 'StockCode', 'Description', 'Quantity', 'Price'] + ADDED].copy()
    audit.insert(0, 'Issue_ID', 'TRANSACTION_PATTERN:' + audit['Source_Row_ID'])
    audit['Issue_Type'] = audit['Transaction_Type']
    audit['Original_Value'] = audit.apply(
        lambda row: json.dumps({'Invoice':row['Invoice'], 'Quantity':row['Quantity']}), axis=1)
    audit['Treatment'] = 'Retain source values; descriptive classification only; review pending'
    audit['Reason'] = 'Invoice/quantity pattern does not establish business cause or physical return'
    account = audit['Transaction_Type'].eq('Accounting adjustment')
    audit.loc[account, 'Treatment'] = 'Carry forward verified accounting classification and existing merchandise KPI exclusion flag'
    audit.loc[account, 'Reason'] = 'Previously reviewed bad-debt adjustment; not a new price treatment'
    if before != sha256(source) or parent_hash != sha256(parent_file):
        raise RuntimeError('Input changed during processing')
    now = datetime.now(timezone.utc)
    folder = args.output/('transaction_patterns_' + now.strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir(parents=True, exist_ok=False)
    output = folder/'transactions_with_pattern_classification.csv'
    frame.to_csv(output, index=False)
    audit.to_csv(folder/'transaction_pattern_audit.csv', index=False)
    exported = pd.read_csv(output, dtype=str, keep_default_na=False)
    if not exported[original_columns].equals(frame[original_columns]):
        raise RuntimeError('Original values or order changed on export; do not use output')
    for name in ['Is_Cancellation', 'Invoice_Quantity_Review_Required']:
        if not exported[name].isin(['True', 'False']).all() or not exported[name].eq('True').equals(added[name]):
            raise RuntimeError('Exported boolean flag failed verification: ' + name)
    if not exported['Transaction_Type'].equals(added['Transaction_Type']):
        raise RuntimeError('Exported classification changed')
    counts = added['Transaction_Type'].value_counts().to_dict()
    if sum(counts.values()) != len(frame) or len(audit) != int(mask.sum()) or not audit['Issue_ID'].is_unique:
        raise RuntimeError('Category/audit reconciliation failed')
    if before != sha256(source) or parent_hash != sha256(parent_file):
        raise RuntimeError('Input changed; do not use outputs')
    summary = {
        'status': 'Observed patterns classified; not final merchandise eligibility or confirmed returns',
        'run_utc': now.isoformat(), 'input_file':str(source), 'input_sha256':before,
        'input_unchanged':True, 'parent_price_summary_sha256':parent_hash,
        'original_workbook_sha256_from_parent':parent.get('original_workbook_sha256_from_parent'),
        'output_sha256':sha256(output), 'script_sha256':sha256(Path(__file__)),
        'python_version':platform.python_version(), 'pandas_version':pd.__version__,
        'input_rows':len(frame), 'output_rows':len(exported), 'rows_removed':0,
        'transaction_type_counts':counts,
        'cancellation_marked_lines':int(added['Is_Cancellation'].sum()),
        'invoice_quantity_review_required':int(added['Invoice_Quantity_Review_Required'].sum()),
        'audit_rows':len(audit), 'prior_flag_counts':prior_counts, 'prior_flags_unchanged':True,
        'checks':'Parent hash/counts and prior flags reconcile; unique provenance; category counts sum to rows; audit reconciles; exported source fields/order/classifications/flags unchanged; input unchanged',
        'scope_limit':'No sign corrections, removals, imputation or return-value calculation. No inferred merchandise sale or physical return. Existing price/exclusion flags retained. Review=False is not global KPI eligibility.'
    }
    (folder/'transaction_pattern_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(f'Rows retained: {len(frame):,}')
    for category, count in counts.items():
        print(f'{category}: {count:,}')
    print(f'Invoice/quantity review required: {summary["invoice_quantity_review_required"]:,}')
    print(f'Pattern audit entries: {len(audit):,}')
    print('Rows removed: 0. All previous flags and original values preserved.')
    print(f'Outputs: {folder}')

if __name__ == '__main__':
    main()
