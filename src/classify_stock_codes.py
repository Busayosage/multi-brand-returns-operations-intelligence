r"""Add descriptive stock-code categories; retain every row and prior field.

Run from portfolio work: .\.venv\Scripts\python.exe src\classify_stock_codes.py
Categories describe observed code/description pairs, not final KPI eligibility.
Numeric-leading codes remain outside this review's scope.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import platform
import re
import pandas as pd

ADDED = ['Stock_Code_Category', 'Stock_Code_Review_Required', 'Stock_Code_Classification_Reason']
DEFAULT_RUN = 'bad_debt_correction_20260917T002114012955Z'
# Exact reviewed pairs after temporary trimming/case normalization.
SPECIAL = {
    ('POST', 'POSTAGE'): 'Delivery charge',
    ('DOT', 'DOTCOM POSTAGE'): 'Delivery charge',
    ('C2', 'CARRIAGE'): 'Delivery charge',
    ('BANK CHARGES', 'BANK CHARGES'): 'Fee',
    ('AMAZONFEE', 'AMAZON FEE'): 'Fee',
    ('CRUK', 'CRUK COMMISSION'): 'Fee',
    ('D', 'DISCOUNT'): 'Discount',
    ('B', 'ADJUST BAD DEBT'): 'Accounting adjustment',
    ('ADJUST', 'ADJUSTMENT BY JOHN ON 26/01/2010 16'): 'Accounting adjustment',
    ('ADJUST', 'ADJUSTMENT BY JOHN ON 26/01/2010 17'): 'Accounting adjustment',
    ('ADJUST', 'ADJUSTMENT BY PETER ON 24/05/2010 1'): 'Accounting adjustment',
    ('ADJUST2', 'ADJUSTMENT BY PETER ON JUN 25 2010'): 'Accounting adjustment',
    ('M', 'MANUAL'): 'Manual entry',
    ('S', 'SAMPLES'): 'Sample',
    ('TEST001', 'THIS IS A TEST PRODUCT.'): 'Test entry',
    ('TEST002', 'THIS IS A TEST PRODUCT.'): 'Test entry',
}
PRODUCTS = {
    'DCGS0058': 'MISO PRETTY  GUM', 'DCGSSGIRL': 'GIRLS PARTY BAG',
    'DCGSSBOY': 'BOYS PARTY BAG', 'PADS': 'PADS TO MATCH ALL CUSHIONS',
    'DCGS0076': 'SUNJAR LED NIGHT NIGHT LIGHT', 'DCGS0003': 'BOXED GLASS ASHTRAY',
    'DCGS0069': 'OOH LA LA DOGS COLLAR', 'DCGS0004': 'HAYNES CAMPER SHOULDER BAG',
    'DCGS0072': 'CAT CAMOUFLAGUE COLLAR', 'SP1002': "KID'S CHALKBOARD/EASEL",
    'DCGS0066N': 'NAVY CUDDLES DOG HOODIE', 'DCGS0070': 'CAMOUFLAGE DOG COLLAR',
    'DCGS0068': 'DOGS NIGHT COLLAR', 'DCGS0037': 'KEY-RING CORKSCREW',
    'DCGS0041': 'HAYNES MINI-COOPER PLAYING CARDS',
    'DCGS0044': 'HANDZ-OFF CAR FRESHENER', 'DCGS0062': 'ROAD-RAGE CAR FRESHENER',
    'DCGS0075': 'CAMOUFLAGUE DOG LEAD',
}

def classify_pair(code, description):
    c, d = code.strip().upper(), description.strip().upper()
    if not c:
        return ('Unclear', True, 'Blank stock code; review required')
    if not d:
        return ('Unclear', True, 'Blank description; no classification inferred from code alone')
    if d in {'EBAY', 'UPDATE'}:
        return ('Unclear', True, 'Description is a channel/update label; business purpose unresolved')
    if (c, d) in SPECIAL:
        category = SPECIAL[(c, d)]
        review = category in {'Manual entry', 'Sample', 'Test entry'}
        return (category, review, 'Reviewed exact code/description pair; ' +
                ('merchandise treatment requires review' if review else 'descriptive category only; no KPI filter applied'))
    voucher = re.fullmatch(r'GIFT_0001_(10|20|30|40|50|60|70|80|90)', c)
    if voucher and d == 'DOTCOMGIFTSHOP GIFT VOUCHER £' + voucher.group(1) + '.00':
        return ('Gift voucher', False, 'Voucher code and denomination description agree; separate voucher category')
    if PRODUCTS.get(c) == d:
        return ('Product candidate', False, 'Reviewed physical-product description; sale/return eligibility not established')
    if re.match(r'^[0-9]', c):
        return ('Numeric-leading code - not assessed', True, 'Outside this non-digit-leading stock-code review; not automatically merchandise')
    return ('Unclear', True, 'No reviewed code/description pair matched')

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=root/'outputs'/DEFAULT_RUN/'transactions_with_corrected_accounting.csv')
    parser.add_argument('--output', type=Path, default=root/'outputs')
    args = parser.parse_args()
    source = args.input.resolve()
    parent_path = source.parent/'bad_debt_correction_summary.json'
    before, parent_hash = sha256(source), sha256(parent_path)
    parent = json.loads(parent_path.read_text(encoding='utf-8'))
    if before != parent['output_sha256']:
        raise ValueError('Input hash differs from correction summary')
    print('Reading corrected transactions...', flush=True)
    frame = pd.read_csv(source, dtype=str, keep_default_na=False)
    original_cols = frame.columns.tolist()
    required = ['StockCode', 'Description', 'Source_Row_ID', 'Source_Period', 'Source_Excel_Row', 'Transaction_Type']
    if not set(required).issubset(frame.columns) or any(c in frame.columns for c in ADDED):
        raise ValueError('Required columns missing or input already classified')
    if len(frame) != parent['output_rows'] or not frame.Source_Row_ID.is_unique or frame.Source_Row_ID.str.strip().eq('').any():
        raise ValueError('Row count or provenance mismatch')
    for name, count in parent['flag_counts'].items():
        if not frame[name].isin(['True', 'False']).all() or int(frame[name].eq('True').sum()) != count:
            raise ValueError('Previous flag count mismatch: ' + name)
    if frame.Transaction_Type.value_counts().to_dict() != parent['transaction_type_counts']:
        raise ValueError('Previous transaction classifications do not reconcile')
    # Classify distinct pairs once, then map results back in original row order.
    pairs = list(zip(frame.StockCode, frame.Description))
    rules = {pair: classify_pair(*pair) for pair in set(pairs)}
    added = pd.DataFrame([rules[pair] for pair in pairs], columns=ADDED, index=frame.index)
    added[ADDED[1]] = added[ADDED[1]].map({True: 'True', False: 'False'})
    result = pd.concat([frame, added], axis=1)
    screened = ~frame.StockCode.str.strip().str.match(r'^[0-9]')
    # Audit all screened rows, including product candidates and unresolved records.
    audit = result.loc[screened].reset_index(drop=True)
    pair_summary = result.groupby(['StockCode', 'Description'] + ADDED, sort=True).size().reset_index(name='Row_Count')
    counts = added[ADDED[0]].value_counts().to_dict()
    if sum(counts.values()) != len(frame) or int(pair_summary.Row_Count.sum()) != len(frame):
        raise RuntimeError('Classification totals failed reconciliation')
    now = datetime.now(timezone.utc)
    folder = args.output/('stock_codes_' + now.strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir(parents=True, exist_ok=False)
    output = folder/'transactions_with_stock_code_categories.csv'
    audit_path = folder/'stock_code_audit.csv'
    result.to_csv(output, index=False)
    audit.to_csv(audit_path, index=False)
    pair_summary.to_csv(folder/'stock_code_pair_summary.csv', index=False)
    exported = pd.read_csv(output, dtype=str, keep_default_na=False)
    if not exported.equals(result) or not exported[original_cols].equals(frame):
        raise RuntimeError('Export verification failed; do not use outputs')
    if not pd.read_csv(audit_path, dtype=str, keep_default_na=False).equals(audit):
        raise RuntimeError('Audit verification failed')
    if before != sha256(source) or parent_hash != sha256(parent_path):
        raise RuntimeError('Input changed during processing; do not use outputs')
    summary = {
        'status': 'Stock-code categories added; final KPI eligibility not implemented',
        'rule_version': '1.0', 'run_utc': now.isoformat(), 'input_file': str(source),
        'input_sha256': before, 'input_unchanged': True, 'parent_correction_summary_sha256': parent_hash,
        'original_workbook_sha256_from_parent': parent.get('original_workbook_sha256_from_parent'),
        'output_sha256': sha256(output), 'script_sha256': sha256(Path(__file__)),
        'python_version': platform.python_version(), 'pandas_version': pd.__version__,
        'input_rows': len(frame), 'output_rows': len(result), 'rows_removed': 0,
        'category_counts': counts, 'non_digit_leading_rows': int(screened.sum()),
        'screened_category_counts': added.loc[screened, ADDED[0]].value_counts().to_dict(),
        'screened_review_required': int(added.loc[screened, ADDED[1]].eq('True').sum()),
        'total_review_required': int(added[ADDED[1]].eq('True').sum()),
        'audit_rows': len(audit), 'prior_flag_counts': parent['flag_counts'], 'prior_flags_unchanged': True,
        'transaction_type_counts': parent['transaction_type_counts'],
        'checks': 'Parent hash/counts reconcile; unique provenance; category and pair counts reconcile; full export and audit readback verified; all previous columns/order preserved; inputs unchanged',
        'scope_limit': 'Numeric-leading codes remain not assessed and review=True. Review=False only means this stock-code pair was categorised, not overall KPI eligibility. No broad prefix exclusion, value filling, row deletion, or changes to existing merchandise exclusion or transaction type flags.',
        'fields': {
            ADDED[0]: 'Descriptive category from reviewed pair rules; helps separate products from charges and adjustments',
            ADDED[1]: 'True for ambiguous, unassessed, manual, sample or test entries; tracks unresolved stock-code treatment',
            ADDED[2]: 'Rule explanation for the category; supports traceability and review'
        }
    }
    (folder/'stock_code_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(f'Rows retained: {len(result):,}')
    print(f'Non-digit-leading rows audited: {len(audit):,}')
    for category, count in summary['screened_category_counts'].items():
        print(f'  {category}: {count:,}')
    print(f'Screened rows requiring review: {summary["screened_review_required"]:,}')
    print('Numeric-leading codes remain not assessed; final KPI filters pending.')
    print('Rows removed: 0. All previous columns and flags preserved.')
    print(f'Outputs: {folder}')

if __name__ == '__main__':
    main()
