r"""Build review reports only; never change transactions or decide KPI eligibility.
Run from the project: .\.venv\Scripts\python.exe src\build_quality_review.py
Requires pandas. --input and --output override the project defaults.
"""
from pathlib import Path
import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'outputs/stock_codes_20260917T004837903105Z/transactions_with_stock_code_categories.csv'
# Exact normalised labels observed in the review: signals, not proven causes.
REVIEW_LABELS = {
    'check', 'checked', '?', '??', 'damages', 'damaged', 'found', 'missing',
    'sold as set on dotcom', 'adjustment', 'dotcom', 'smashed', 'thrown away',
    'unsaleable, destroyed.', 'amazon', 'damages?', 'ebay', 'update',
}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DEFAULT)
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs')
    args = parser.parse_args()
    source = args.input.resolve()
    parent_path = source.with_name('stock_code_summary.json')
    parent_hash = digest(parent_path)
    parent = json.loads(parent_path.read_text(encoding='utf-8'))
    source_hash = digest(source)
    require(source_hash == parent['output_sha256'], 'Input does not match stock-code summary checksum.')
    print('Reading stock-code-classified transactions...')
    df = pd.read_csv(source, dtype=str, keep_default_na=False)
    require(len(df) == parent['output_rows'], 'Parent row count mismatch.')
    require(df['Source_Row_ID'].str.strip().ne('').all() and df['Source_Row_ID'].is_unique,
            'Source row IDs must be present and unique.')
    for column, expected in parent['prior_flag_counts'].items():
        require(df[column].isin(['True', 'False']).all(), f'Invalid Boolean: {column}')
        require(int(df[column].eq('True').sum()) == expected, f'Flag count mismatch: {column}')
    require(df['Stock_Code_Review_Required'].isin(['True', 'False']).all(), 'Invalid stock review flag.')
    require(df['Stock_Code_Category'].value_counts().to_dict() == parent['category_counts'], 'Category mismatch.')
    require(df['Transaction_Type'].value_counts().to_dict() == parent['transaction_type_counts'], 'Pattern mismatch.')

    numeric = df['StockCode'].str.strip().str.match(r'^[0-9]')
    description = df['Description'].str.strip()
    dates_raw = df['InvoiceDate'].str.strip()
    # The prior exports use ISO timestamps. No ambiguous day/month guessing.
    date_shape = dates_raw.str.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
    dates = pd.to_datetime(dates_raw.where(date_shape), format='%Y-%m-%d %H:%M:%S', errors='coerce')
    flags = pd.DataFrame(index=df.index)
    for col in ['Missing_Customer_ID', 'Missing_Description', 'Zero_Price',
                'Negative_Price', 'Invoice_Quantity_Review_Required']:
        flags[col] = df[col].eq('True')
    flags['Description_Label_Review'] = description.str.casefold().isin(REVIEW_LABELS)
    flags['Missing_InvoiceDate'] = dates_raw.eq('')
    flags['Invalid_InvoiceDate'] = dates_raw.ne('') & dates.isna()
    any_issue = flags.any(axis=1)
    scope = pd.Series('Non-digit-leading', index=df.index)
    scope.loc[numeric] = 'Numeric-leading'
    run = datetime.now(timezone.utc)
    out = args.output.resolve() / ('quality_review_' + run.strftime('%Y%m%dT%H%M%S%fZ'))
    out.mkdir(parents=True, exist_ok=False)
    hashes = {}

    def save(frame, name):
        path = out / name
        frame.to_csv(path, index=False)
        reread = pd.read_csv(path, dtype=str, keep_default_na=False)
        pd.testing.assert_frame_equal(reread, frame.reset_index(drop=True).astype(str), check_dtype=False)
        hashes[name] = digest(path)

    overlaps = flags.copy()
    overlaps.insert(0, 'Code_Scope', scope)
    combinations = overlaps.groupby(list(overlaps.columns), dropna=False).size().reset_index(name='Rows')
    require(int(combinations['Rows'].sum()) == len(df), 'Overlap groups do not reconcile.')
    save(combinations, 'flag_overlap_summary.csv')
    descriptions = pd.DataFrame({
        'Code_Scope': scope, 'StockCode': df['StockCode'], 'Description': df['Description'],
        'Stock_Code_Category': df['Stock_Code_Category'], 'Transaction_Type': df['Transaction_Type'],
        'Missing_Description': flags['Missing_Description'],
        'Description_Label_Review': flags['Description_Label_Review'],
        'Zero_Price': flags['Zero_Price'],
        'Invoice_Quantity_Review_Required': flags['Invoice_Quantity_Review_Required'],
    })
    pairs = descriptions.groupby(list(descriptions.columns), dropna=False).size().reset_index(name='Rows')
    require(int(pairs['Rows'].sum()) == len(df), 'Description groups do not reconcile.')
    save(pairs.sort_values('Rows', ascending=False), 'description_review_summary.csv')
    # One audit entry per affected source row, even when several flags apply.
    audit = df.loc[any_issue].copy()
    for col in flags.columns:
        if col not in audit.columns:
            audit[col] = flags.loc[any_issue, col]
    audit['Review_Flag_Count'] = flags.loc[any_issue].sum(axis=1)
    save(audit, 'quality_review_audit.csv')
    monthly = pd.DataFrame({'Source_Period': df['Source_Period'], 'Invoice_Month': dates.dt.strftime('%Y-%m').fillna('[UNPARSED]')})
    monthly = monthly.groupby(['Source_Period', 'Invoice_Month']).size().reset_index(name='Rows')
    require(int(monthly['Rows'].sum()) == len(df), 'Monthly counts do not reconcile.')
    save(monthly, 'invoice_month_summary.csv')
    date_audit = df.loc[dates.isna()].copy()
    date_audit['Date_Review_Reason'] = flags.loc[dates.isna(), 'Missing_InvoiceDate'].map({True: 'Missing', False: 'Invalid or unexpected format'})
    save(date_audit, 'invoice_date_audit.csv')
    require(digest(source) == source_hash and digest(parent_path) == parent_hash, 'Inputs changed during review.')
    summary = {
        'status': 'Review reports completed; no transaction changes or final KPI eligibility decisions',
        'run_utc': run.isoformat(), 'input_file': str(source), 'input_sha256': source_hash,
        'parent_summary_sha256': parent_hash, 'input_unchanged': True,
        'original_workbook_sha256_from_parent': parent['original_workbook_sha256_from_parent'],
        'script_sha256': digest(Path(__file__)), 'python_version': platform.python_version(),
        'pandas_version': pd.__version__, 'input_rows': len(df), 'rows_removed': 0,
        'numeric_leading_rows': int(numeric.sum()),
        'flag_counts': {c: int(flags[c].sum()) for c in flags},
        'numeric_leading_flag_counts': {c: int(flags.loc[numeric, c].sum()) for c in flags},
        'unique_rows_with_review_flags': int(any_issue.sum()),
        'rows_with_multiple_review_flags': int(flags.sum(axis=1).gt(1).sum()),
        'rows_without_these_review_flags': int((~any_issue).sum()),
        'valid_date_rows': int(dates.notna().sum()),
        'date_min': str(dates.min()) if dates.notna().any() else None,
        'date_max': str(dates.max()) if dates.notna().any() else None,
        'output_hashes': hashes,
        'rules': {
            'Description_Label_Review': 'Exact stripped, case-insensitive match to observed labels; a review signal only.',
            'description_review_labels': sorted(REVIEW_LABELS),
            'InvoiceDate': 'Strict YYYY-MM-DD HH:MM:SS parsing; unexpected formats require review, not automatic correction.',
            'Review_Flag_Count': 'Number of the eight report flags true for a row; supports overlap analysis.',
        },
        'scope_limit': 'Flag counts overlap. All descriptions are grouped, but semantic validity is not established. No-flag rows are not automatically merchandise or KPI eligible. Stock-code pending review and cancellation/repetition flags are preserved in audits but are not included in the eight issue flags. Date validity means parseability only. No source fields, prior flags, signs or classifications changed.',
        'checks': 'Parent hash, row count, unique provenance, prior flags, categories and patterns reconcile; all report CSVs read back exactly; grouped counts reconcile; source and parent unchanged.',
    }
    (out / 'quality_review_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(f'Rows reviewed: {len(df):,}')
    print(f'Unique rows with review flags: {int(any_issue.sum()):,}')
    print(f'Rows with multiple flags: {summary["rows_with_multiple_review_flags"]:,}')
    print(f'Missing dates: {int(flags["Missing_InvoiceDate"].sum()):,}; invalid/unexpected dates: {int(flags["Invalid_InvoiceDate"].sum()):,}')
    print(f'Date range: {summary["date_min"]} to {summary["date_max"]}')
    print('Rows removed: 0. Source and previous outputs unchanged. KPI rules remain pending.')
    print(f'Outputs: {out}')


if __name__ == '__main__':
    main()
