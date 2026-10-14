r"""Add a missing-description flag and audit log; preserve every input value.

Run from portfolio work:
  .\.venv\Scripts\python.exe src\flag_missing_descriptions.py

Missing_Description is True for empty or whitespace-only Description values.
It identifies incomplete product labelling, not invalid transactions. False
means present, not validated. No stock-code mapping or filling is performed.
Existing Missing_Customer_ID flags are carried forward unchanged.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import platform
import pandas as pd

DEFAULT_RUN = 'customer_id_20260916T214859255337Z'

def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def missing_descriptions(series):
    # Inspect a temporary stripped copy. Do not change the Description column.
    return series.str.strip().eq('')

def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path,
        default=root/'outputs'/DEFAULT_RUN/'transactions_with_customer_id_flag.csv')
    parser.add_argument('--output', type=Path, default=root/'outputs')
    args = parser.parse_args()
    source = args.input.resolve()
    parent_file = source.parent/'customer_id_summary.json'
    if not source.is_file() or not parent_file.is_file():
        raise FileNotFoundError('Expected the customer-ID CSV and customer_id_summary.json in: ' + str(source.parent))
    parent_hash = sha256(parent_file)
    previous = json.loads(parent_file.read_text(encoding='utf-8'))
    before = sha256(source)
    if before != previous['output_sha256']:
        raise ValueError('Input checksum differs from the customer-ID summary; stop and review the selected file')
    print('Reading transactions with customer-ID flags...', flush=True)
    frame = pd.read_csv(source, dtype=str, keep_default_na=False)
    original_columns = frame.columns.tolist()
    required = ['Description', 'StockCode', 'Customer ID', 'Missing_Customer_ID',
                'Source_Row_ID', 'Source_Period', 'Source_Excel_Row']
    if not all(name in frame.columns for name in required):
        raise ValueError('Required source or customer-flag columns are missing')
    if 'Missing_Description' in frame.columns:
        raise ValueError('Input already contains Missing_Description; select the previous customer-ID output')
    if len(frame) != previous['output_rows']:
        raise ValueError('Row count differs from the customer-ID summary')
    if not frame['Source_Row_ID'].is_unique or frame['Source_Row_ID'].str.strip().eq('').any():
        raise ValueError('Source_Row_ID must be unique and nonblank')
    flags = frame['Missing_Customer_ID']
    if not flags.isin(['True', 'False']).all():
        raise ValueError('Unexpected customer-flag values')
    if int(flags.eq('True').sum()) != previous['missing_customer_ids']:
        raise ValueError('Customer-flag count differs from the previous summary')
    missing = missing_descriptions(frame['Description'])
    frame['Missing_Description'] = missing
    audit = frame.loc[missing, ['Source_Row_ID', 'Source_Period', 'Source_Excel_Row',
                               'StockCode', 'Description']].copy()
    audit = audit.rename(columns={'Description': 'Original_Value'})
    audit.insert(0, 'Issue_ID', 'MISSING_DESCRIPTION:' + audit['Source_Row_ID'])
    audit['Issue_Type'] = 'Missing Description'
    audit['Treatment'] = 'Retain transaction; flag missing description; leave original value unchanged'
    audit['Reason'] = 'Preserve transaction evidence; any later StockCode mapping requires separate verification'
    if before != sha256(source) or parent_hash != sha256(parent_file):
        raise RuntimeError('Input or parent summary changed during processing')
    now = datetime.now(timezone.utc)
    folder = args.output/('description_' + now.strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir(parents=True, exist_ok=False)
    output = folder/'transactions_with_description_flag.csv'
    frame.to_csv(output, index=False)
    audit.to_csv(folder/'missing_description_audit.csv', index=False)
    exported = pd.read_csv(output, dtype=str, keep_default_na=False)
    if not exported[original_columns].equals(frame[original_columns]):
        raise RuntimeError('Original fields or row order changed on export; do not use this output')
    if not exported['Missing_Description'].eq('True').equals(missing):
        raise RuntimeError('Exported description flag failed verification')
    if len(audit) != int(missing.sum()) or not audit['Issue_ID'].is_unique:
        raise RuntimeError('Audit reconciliation failed')
    if before != sha256(source) or parent_hash != sha256(parent_file):
        raise RuntimeError('Input or parent summary changed; do not use this output')
    summary = {
        'status': 'Missing-description flag added; no values filled or rows removed',
        'run_utc': now.isoformat(), 'input_file': str(source),
        'input_sha256': before, 'input_unchanged': True,
        'parent_customer_summary_sha256': parent_hash,
        'original_workbook_sha256_from_parent': previous.get('original_workbook_sha256_from_parent'),
        'output_sha256': sha256(output), 'script_sha256': sha256(Path(__file__)),
        'python_version': platform.python_version(), 'pandas_version': pd.__version__,
        'input_rows': len(frame), 'output_rows': len(exported), 'rows_removed': 0,
        'missing_descriptions': int(missing.sum()), 'present_descriptions': int((~missing).sum()),
        'missing_percentage': round(float(missing.mean()*100), 2) if len(frame) else 0,
        'audit_rows': len(audit), 'missing_customer_ids_carried_forward': int(flags.eq('True').sum()),
        'customer_flags_unchanged': exported['Missing_Customer_ID'].equals(flags),
        'rule': 'Empty or whitespace-only Description; preserve original values; no stock-code mapping or filling',
        'checks': 'Input hash matches parent; row counts match; unique provenance; audit reconciles; all original columns and row order preserved through CSV readback; both flags verified',
        'scope_limit': 'Description presence only, not semantic validity or product identity; no other cleaning'
    }
    (folder/'description_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(f'Rows retained: {len(frame):,}')
    print(f'Missing descriptions: {summary["missing_descriptions"]:,}')
    print(f'Present descriptions: {summary["present_descriptions"]:,}')
    print(f'Missing percentage: {summary["missing_percentage"]:.2f}%')
    print(f'Missing customer-ID flags preserved: {summary["missing_customer_ids_carried_forward"]:,}')
    print('Rows removed: 0. Original values and previous files unchanged.')
    print(f'Outputs: {folder}')

if __name__ == '__main__':
    main()
