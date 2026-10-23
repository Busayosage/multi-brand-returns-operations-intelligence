"""Correct one reviewed positive-price bad-debt entry; preserve source values."""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import argparse
import hashlib
import json
import platform
import pandas as pd

TARGET = 'Year 2010-2011!299984'
DEFAULT_RUN = 'transaction_patterns_20260916T233225078437Z'
CHANGES = {
    'Bad_Debt_Adjustment': ('False', 'True'),
    'Exclude_From_Merchandise_KPIs': ('False', 'True'),
    'Transaction_Type': ('Other movement - not yet classified', 'Accounting adjustment'),
}

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def correct(frame):
    mask = frame['Source_Row_ID'].eq(TARGET)
    if int(mask.sum()) != 1:
        raise ValueError('Expected exactly one reviewed source row: ' + TARGET)
    row = frame.loc[mask].iloc[0]
    expected = {'Invoice': 'A563185', 'StockCode': 'B', 'Description': 'Adjust bad debt',
                'Source_Period': 'Year 2010-2011', 'Source_Excel_Row': '299984'}
    if any(row[k] != v for k, v in expected.items()):
        raise ValueError('Reviewed source fields differ; no correction applied')
    if Decimal(row['Price']) != Decimal('11062.06') or Decimal(row['Quantity']) != 1:
        raise ValueError('Reviewed price/quantity differ; no correction applied')
    for name, (old, new) in CHANGES.items():
        if row[name] != old:
            raise ValueError('Unexpected prior classification: ' + name)
    result = frame.copy()
    for name, (old, new) in CHANGES.items():
        result.loc[mask, name] = new
    audit = frame.loc[mask, ['Source_Row_ID', 'Source_Period', 'Source_Excel_Row',
                            'Invoice', 'StockCode', 'Description', 'Quantity', 'Price']].copy()
    for name, (old, new) in CHANGES.items():
        audit[name + '_Before'] = old
        audit[name + '_After'] = new
    audit['Reason'] = 'Reviewed B / Adjust bad debt entry is an accounting adjustment regardless of price sign; reversal not established'
    return result, audit.reset_index(drop=True)

def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=root/'outputs'/DEFAULT_RUN/'transactions_with_pattern_classification.csv')
    parser.add_argument('--output', type=Path, default=root/'outputs')
    args = parser.parse_args()
    source = args.input.resolve()
    parent_file = source.parent/'transaction_pattern_summary.json'
    before, parent_hash = sha256(source), sha256(parent_file)
    parent = json.loads(parent_file.read_text(encoding='utf-8'))
    if before != parent['output_sha256']:
        raise ValueError('Input checksum differs from parent summary')
    print('Reading classified transactions...', flush=True)
    frame = pd.read_csv(source, dtype=str, keep_default_na=False)
    if len(frame) != parent['output_rows'] or not frame['Source_Row_ID'].is_unique or frame['Source_Row_ID'].str.strip().eq('').any():
        raise ValueError('Input row count/provenance mismatch')
    flags = list(parent['prior_flag_counts']) + ['Is_Cancellation', 'Invoice_Quantity_Review_Required']
    for name in flags:
        if not frame[name].isin(['True', 'False']).all():
            raise ValueError('Invalid boolean flag: ' + name)
    for name, count in parent['prior_flag_counts'].items():
        if int(frame[name].eq('True').sum()) != count:
            raise ValueError('Parent flag count mismatch: ' + name)
    if frame['Transaction_Type'].value_counts().to_dict() != parent['transaction_type_counts']:
        raise ValueError('Parent transaction counts differ')
    for name, key in [('Is_Cancellation', 'cancellation_marked_lines'), ('Invoice_Quantity_Review_Required', 'invoice_quantity_review_required')]:
        if int(frame[name].eq('True').sum()) != parent[key]:
            raise ValueError('Parent pattern flag count mismatch')
    result, audit = correct(frame)
    changed = result.ne(frame)
    if int(changed.to_numpy().sum()) != 3 or int(changed.any(axis=1).sum()) != 1:
        raise RuntimeError('Expected exactly three classification changes on one row')
    immutable = [c for c in frame.columns if c not in CHANGES]
    if not result[immutable].equals(frame[immutable]):
        raise RuntimeError('An immutable value changed')
    now = datetime.now(timezone.utc)
    folder = args.output/('bad_debt_correction_' + now.strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir(parents=True, exist_ok=False)
    output = folder/'transactions_with_corrected_accounting.csv'
    audit_path = folder/'bad_debt_correction_audit.csv'
    result.to_csv(output, index=False)
    audit.to_csv(audit_path, index=False)
    exported = pd.read_csv(output, dtype=str, keep_default_na=False)
    if not exported.equals(result) or not pd.read_csv(audit_path, dtype=str, keep_default_na=False).equals(audit):
        raise RuntimeError('Export verification failed; do not use output')
    if sha256(source) != before or sha256(parent_file) != parent_hash:
        raise RuntimeError('Input changed during processing; do not use output')
    counts = {name: int(result[name].eq('True').sum()) for name in flags}
    summary = {
        'status': 'One reviewed accounting classification corrected; KPI filters not implemented',
        'run_utc': now.isoformat(), 'input_file': str(source), 'input_sha256': before,
        'input_unchanged': True, 'parent_transaction_summary_sha256': parent_hash,
        'original_workbook_sha256_from_parent': parent.get('original_workbook_sha256_from_parent'),
        'output_sha256': sha256(output), 'audit_sha256': sha256(audit_path),
        'script_sha256': sha256(Path(__file__)), 'python_version': platform.python_version(),
        'pandas_version': pd.__version__, 'input_rows': len(frame), 'output_rows': len(result),
        'rows_removed': 0, 'corrected_rows': 1, 'changed_cells': 3, 'audit_rows': len(audit),
        'corrected_source_row_id': TARGET, 'changes': CHANGES,
        'flag_counts': counts, 'transaction_type_counts': result['Transaction_Type'].value_counts().to_dict(),
        'checks': 'Parent checksum/counts reconciled; unique provenance; exactly three approved cells on one row changed; full CSV and audit readback verified; inputs unchanged',
        'scope_limit': 'Original price remains positive 11062.06. No inferred reversal, sign changes, row removal or other classification. All other flags preserved. Prior audit files remain unchanged; this audit records only the correction.'
    }
    (folder/'bad_debt_correction_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(f'Rows retained: {len(result):,}')
    print('Corrected rows: 1; classification fields changed: 3')
    print(f'Bad-debt adjustments: {counts["Bad_Debt_Adjustment"]:,}')
    print(f'Merchandise KPI exclusion flags: {counts["Exclude_From_Merchandise_KPIs"]:,}')
    print(f'Negative prices unchanged: {counts["Negative_Price"]:,}')
    print('Rows removed: 0. Source values and all other flags preserved.')
    print(f'Outputs: {folder}')

if __name__ == '__main__':
    main()
