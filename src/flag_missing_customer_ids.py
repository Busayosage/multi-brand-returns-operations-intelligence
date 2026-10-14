r"""Flag missing customer IDs without dropping rows or filling source values.

Run from portfolio work:
  .\.venv\Scripts\python.exe src\flag_missing_customer_ids.py

Default input is the user's verified cross-sheet run. Use --input PATH for
another explicitly chosen run. pandas is the only external dependency.

Data dictionary:
  Missing_Customer_ID = True when Customer ID is empty/whitespace-only.
  False means a value is present, NOT that the identifier is fully validated.
Purpose: retain transaction coverage and identify rows that cannot be used
to identify individual customers. Customer-specific KPI eligibility must
explicitly filter this flag, alongside any later validity rules.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import platform
import pandas as pd

DEFAULT_RUN = 'cross_sheet_20260916T134335398702Z'

def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def missing_ids(series):
    # Only inspect a stripped copy; do not trim the source Customer ID column.
    # Literal strings such as 'NA' or 'nan' are NOT assumed missing.
    return series.str.strip().eq('')

def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path,
        default=root/'outputs'/DEFAULT_RUN/'transactions_after_cross_sheet_matching.csv')
    parser.add_argument('--output', type=Path, default=root/'outputs')
    args = parser.parse_args()
    source = args.input.resolve()
    parent_summary = source.parent/'matching_summary.json'
    if not source.is_file() or not parent_summary.is_file():
        raise FileNotFoundError('Both the cross-sheet CSV and its matching_summary.json must exist: ' + str(source.parent))
    previous = json.loads(parent_summary.read_text(encoding='utf-8'))
    before = sha256(source)
    print('Reading retained transactions...', flush=True)
    # Preserve every CSV value as text, including leading zeros, blanks,
    # literal NA strings and previous provenance/flags. No numeric inference.
    frame = pd.read_csv(source, dtype=str, keep_default_na=False)
    original_columns = frame.columns.tolist()
    required = ['Customer ID', 'Source_Row_ID', 'Source_Period', 'Source_Excel_Row']
    if not all(name in frame.columns for name in required):
        raise ValueError('Required source/provenance columns are missing')
    if 'Missing_Customer_ID' in frame.columns:
        raise ValueError('Input is already flagged; use the original cross-sheet CSV')
    if len(frame) != previous['retained_rows']:
        raise ValueError('Input row count differs from the cross-sheet summary')
    if not frame['Source_Row_ID'].is_unique or frame['Source_Row_ID'].str.strip().eq('').any():
        raise ValueError('Source_Row_ID must be nonblank and unique')
    original_ids = frame['Customer ID'].copy()
    missing = missing_ids(frame['Customer ID'])
    frame['Missing_Customer_ID'] = missing
    audit = frame.loc[missing, ['Source_Row_ID', 'Source_Period', 'Source_Excel_Row', 'Customer ID']].copy()
    audit = audit.rename(columns={'Customer ID': 'Original_Value'})
    audit.insert(0, 'Issue_ID', 'MISSING_CUSTOMER_ID:' + audit['Source_Row_ID'])
    audit['Issue_Type'] = 'Missing Customer ID'
    audit['Treatment'] = 'Retain transaction; flag missing ID; leave original value unchanged'
    audit['Reason'] = 'Transaction may support eligible non-customer analysis; cannot identify an individual customer'
    if before != sha256(source):
        raise RuntimeError('Input changed during execution; no outputs written')
    assert frame['Customer ID'].equals(original_ids)
    assert len(audit) == int(missing.sum()) and audit['Issue_ID'].is_unique
    now = datetime.now(timezone.utc)
    destination = args.output/('customer_id_' + now.strftime('%Y%m%dT%H%M%S%fZ'))
    destination.mkdir(parents=True, exist_ok=False)
    output = destination/'transactions_with_customer_id_flag.csv'
    frame.to_csv(output, index=False)
    audit.to_csv(destination/'missing_customer_id_audit.csv', index=False)
    # Verify the exported copy retained every original field and row order.
    reread = pd.read_csv(output, dtype=str, keep_default_na=False)
    if not reread[original_columns].equals(frame[original_columns]):
        raise RuntimeError('Output round-trip changed original values; do not use this output')
    assert reread['Missing_Customer_ID'].eq('True').equals(missing)
    summary = {
        'status': 'Missing-customer flag added; other cleaning not started',
        'run_utc': now.isoformat(), 'input_file': str(source),
        'input_sha256': before, 'input_unchanged': sha256(source) == before,
        'parent_matching_summary_sha256': sha256(parent_summary),
        'original_workbook_sha256_from_parent': previous.get('source_sha256'),
        'output_sha256': sha256(output), 'script_sha256': sha256(Path(__file__)),
        'python_version': platform.python_version(), 'pandas_version': pd.__version__,
        'input_rows': len(frame), 'output_rows': len(reread), 'rows_removed': 0,
        'missing_customer_ids': int(missing.sum()),
        'present_customer_ids': int((~missing).sum()),
        'missing_percentage': round(float(missing.mean()*100), 2) if len(frame) else 0,
        'audit_rows': len(audit),
        'rule': 'Empty or whitespace-only Customer ID; no invented IDs or value replacement',
        'checks': 'Row count matches parent; unique source IDs; audit count reconciles; exported source fields and row order unchanged; flag round-trip verified',
        'scope_limit': 'ID presence only, not identifier validity, customer uniqueness, or full KPI eligibility'
    }
    if not summary['input_unchanged']:
        raise RuntimeError('Input changed; do not use this output')
    (destination/'customer_id_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(f'Rows retained: {len(frame):,}')
    print(f'Missing customer IDs: {summary["missing_customer_ids"]:,}')
    print(f'Present customer IDs: {summary["present_customer_ids"]:,}')
    print(f'Missing percentage: {summary["missing_percentage"]:.2f}%')
    print('Rows removed: 0. Original values and previous files unchanged.')
    print(f'Outputs: {destination}')

if __name__ == '__main__':
    main()
