r"""Apply the approved one-for-one cross-sheet rule, without editing the source.

From the project folder on Windows:
  .\.venv\Scripts\python.exe src\resolve_cross_sheet_duplicates.py

Requires pandas and openpyxl. No other cleaning is performed.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import platform
import pandas as pd

FIELDS = ['Invoice', 'StockCode', 'Description', 'Quantity', 'InvoiceDate',
          'Price', 'Customer ID', 'Country']
SHEETS = ['Year 2009-2010', 'Year 2010-2011']

def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def annotate(frame, sheet):
    """Add provenance and count identical occurrences within this source sheet."""
    if frame.columns.tolist() != FIELDS:
        raise ValueError(f'Unexpected source columns in {sheet}: {frame.columns.tolist()}')
    result = frame.copy()
    result['Source_Period'] = sheet
    result['Source_Excel_Row'] = range(2, len(result) + 2)
    result['Source_Row_ID'] = sheet + '!' + result['Source_Excel_Row'].astype(str)
    result['Within_Sheet_Repetition'] = result.duplicated(FIELDS, keep=False)
    result['Within_Sheet_Occurrence'] = result.groupby(
        FIELDS, dropna=False, sort=False).cumcount() + 1
    return result

def resolve(first, second):
    """Keep all of first; exclude only paired occurrences from second.

    For a value combination occurring a times in first and b times in second,
    exclude min(a,b) from second and retain max(a,b) overall.
    """
    keys = FIELDS + ['Within_Sheet_Occurrence']
    matches = first[keys + ['Source_Row_ID']].rename(
        columns={'Source_Row_ID': 'Matched_Source_Row_ID'})
    checked = second.merge(matches, on=keys, how='left', validate='one_to_one',
                           sort=False, indicator=True)
    excluded = checked.loc[checked['_merge'].eq('both')].drop(columns='_merge').copy()
    excluded['Treatment'] = 'Excluded from analytical copy; original source preserved'
    excluded['Reason'] = 'All eight source fields and within-sheet occurrence matched in first sheet'
    unpaired = checked.loc[checked['_merge'].eq('left_only'), first.columns].copy()
    retained = pd.concat([first, unpaired], ignore_index=True)
    # These flags refer to repetitions in the original sheet, before exclusions.
    flags = pd.concat([first, second], ignore_index=True)
    flags = flags.loc[flags['Within_Sheet_Repetition']].copy()
    flags['Cross_Sheet_Decision'] = flags['Source_Row_ID'].isin(excluded['Source_Row_ID']).map(
        {True: 'Excluded cross-sheet counterpart', False: 'Retained'})
    assert len(retained) + len(excluded) == len(first) + len(second)
    assert retained['Source_Row_ID'].is_unique
    assert excluded['Source_Row_ID'].is_unique
    assert excluded['Matched_Source_Row_ID'].is_unique
    assert not set(retained['Source_Row_ID']) & set(excluded['Source_Row_ID'])
    # Independently check multiplicity: retain max(count in first, count in second).
    counts = pd.concat([first, second]).groupby(FIELDS, dropna=False, sort=False)['Source_Period'].value_counts()
    expected = int(counts.groupby(level=list(range(len(FIELDS))), dropna=False, sort=False).max().sum())
    assert len(retained) == expected, 'Multiplicity reconciliation failed'
    return retained, excluded, flags

def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=root/'Data'/'Raw'/'online_retail_II.xlsx')
    parser.add_argument('--output', type=Path, default=root/'outputs')
    args = parser.parse_args()
    if not args.input.is_file():
        raise FileNotFoundError(f'Workbook not found: {args.input}')
    before = sha256(args.input)
    frames = []
    with pd.ExcelFile(args.input, engine='openpyxl') as book:
        if book.sheet_names != SHEETS:
            raise ValueError(f'Expected the two approved sheets; found {book.sheet_names}')
        for sheet in SHEETS:
            print(f'Reading {sheet}...', flush=True)
            # Preserve text such as "NA" and mixed identifier types. Blank cells
            # stay empty strings; do not trim, uppercase, fill or round values.
            frame = pd.read_excel(book, sheet_name=sheet, dtype=object, keep_default_na=False)
            frames.append(annotate(frame, sheet))
            print(f'{len(frame):,} source rows loaded.', flush=True)
    retained, excluded, flags = resolve(*frames)
    if before != sha256(args.input):
        raise RuntimeError('Source file changed during execution; no outputs written.')
    now = datetime.now(timezone.utc)
    folder = args.output / ('cross_sheet_' + now.strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir(parents=True, exist_ok=False)
    # This is an intermediate analytical copy, NOT the final clean_transactions.
    retained.to_csv(folder/'transactions_after_cross_sheet_matching.csv', index=False)
    excluded.to_csv(folder/'cross_sheet_exclusion_log.csv', index=False)
    flags.to_csv(folder/'within_sheet_repetition_review.csv', index=False)
    summary = {
        'status': 'Approved cross-sheet rule applied; other cleaning not started',
        'run_utc': now.isoformat(), 'source_file': args.input.name,
        'source_sha256': before, 'source_unchanged': True,
        'python_version': platform.python_version(), 'pandas_version': pd.__version__,
        'script_sha256': sha256(Path(__file__)),
        'source_rows': {name: len(frame) for name, frame in zip(SHEETS, frames)},
        'total_source_rows': sum(map(len, frames)),
        'excluded_cross_sheet_rows': len(excluded), 'retained_rows': len(retained),
        'original_within_sheet_flagged_rows': len(flags),
        'retained_within_sheet_flagged_rows': int(retained['Within_Sheet_Repetition'].sum()),
        'retained_duplicate_excess': int(retained.duplicated(FIELDS).sum()),
        'checks': 'Source hash unchanged; row reconciliation; unique provenance; unique one-for-one matches; multiplicity max(a,b) verified',
        'match_rule': 'All eight source values plus within-sheet occurrence number; first sheet has priority',
        'scope_limit': 'No missing-value, price, quantity, identifier, cancellation or synthetic-data treatment',
        'csv_note': 'CSV is an export; reload identifiers explicitly as text and parse dates when modelling. The original XLSX remains authoritative.'
    }
    (folder/'matching_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(f'\nOriginal rows: {summary["total_source_rows"]:,}')
    print(f'Excluded cross-sheet counterparts: {len(excluded):,}')
    print(f'Retained rows: {len(retained):,}')
    print('Original workbook unchanged. No other cleaning applied.')
    print(f'Outputs: {folder}')

if __name__ == '__main__':
    main()
