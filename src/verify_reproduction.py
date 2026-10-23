"""Check rebuilt data, execute recovered read-only SQL and retain local evidence."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def statements(text):
    buffer = ''
    for char in text:
        buffer += char
        if char == ';' and sqlite3.complete_statement(buffer):
            yield buffer
            buffer = ''
    if buffer.strip():
        yield buffer


def verify(run_dir, saved_validation=None, expected_synthetic=None):
    run_dir = run_dir.resolve()
    report = {'status': 'RUNNING', 'checks': [], 'sql': {}}
    target = run_dir / 'verification.json'

    def check(name, ok):
        report['checks'].append({'name': name, 'pass': bool(ok)})
        if not ok:
            raise ValueError(name)

    try:
        manifest = json.loads((run_dir / 'run_manifest.json').read_text())
        check('All 14 pipeline stages passed', manifest['status'] == 'PASS' and len(manifest['stages']) == 14 and all(s['exit_code'] == 0 for s in manifest['stages']))
        database = run_dir / 'database/retail_analytics.db'
        before = sha(database)
        with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as con:
            con.execute('PRAGMA query_only=ON')
            check('SQLite integrity', con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok')
            check('Foreign keys', not con.execute('PRAGMA foreign_key_check').fetchall())
            check('Money scale is thousandths GBP', dict(con.execute('SELECT * FROM import_metadata'))['money_scale'] == '1000')
            check('Retained source rows', con.execute('SELECT COUNT(*) FROM source_transactions').fetchone()[0] == 1044848)
            for year, gross, cancelled, orders in [('2010', 8628418424, 221407480, 18077), ('2011', 8878008023, 286989560, 17407)]:
                actual = con.execute('SELECT SUM(gross_units),SUM(cancellation_units),COUNT(DISTINCT CASE WHEN sales_eligible=1 THEN invoice_key END) FROM analysis_transactions WHERE month BETWEEN ? AND ?', (year+'-01', year+'-11')).fetchone()
                check(year + ' exact headline numerators and orders', actual == (gross, cancelled, orders))
            for path in sorted((ROOT / 'sql').glob('[0-9]*.sql')):
                results = []
                for query in statements(path.read_text()):
                    cur = con.execute(query)
                    results.append({'columns': [c[0] for c in cur.description], 'rows': cur.fetchall()})
                report['sql'][path.name] = results
            check('All 15 SQL files / 18 statements executed', len(report['sql']) == 15 and sum(map(len, report['sql'].values())) == 18)
            sensitivity = report['sql']['10_cancellation_pair_sensitivity.sql'][0]['rows']
            check('Both-record sensitivity 2.38%; headline 3.23%; net unchanged', [r[-1] for r in sensitivity] == [3.23, 2.38] and sensitivity[0][-2] == sensitivity[1][-2])
            countries = {r[0]: r[3] for r in report['sql']['11_country_year_comparison.sql'][0]['rows']}
            check('Country changes', countries['Australia'] == 106675.5 and countries['EIRE'] == -81105.23)
            products = report['sql']['07_top_cancellation_products_2011.sql'][0]['rows']
            check('Product 23166 cancellation value', products[0][0] == '23166' and products[0][3] == 77479.64)
        check('Database unchanged by verification', sha(database) == before)
        exported = json.loads((run_dir / manifest['dashboard_export'] / 'validation_report.json').read_text())
        check('Export all-field readback and 28-scope internal reconciliation', exported['status'] == 'PASS' and exported['all_exported_fields_readback_match'] and len(exported['exact_kpis']) == 28)
        if saved_validation:
            saved = json.loads(saved_validation.read_text())
            check('Eight measures in all 28 saved scopes', exported['exact_kpis'] == saved['exact_kpis'])
            check('Saved eligibility counts', exported['eligibility_status_counts'] == saved['eligibility_status_counts'])
            for filename in ('dashboard_transactions.csv', 'kpi_reference.csv'):
                check('Saved byte checksum: ' + filename, exported['output_sha256'][filename] == saved['output_sha256'][filename])
        else:
            report['saved_baseline_comparison'] = 'NOT RUN: no saved validation file supplied'
        part2 = json.loads((run_dir / 'outputs/part2/part2_results.json').read_text())
        synthetic = part2['entirely_separate_synthetic_logistics_scenario']
        check('Synthetic baseline', (synthetic['seed'], synthetic['case_count'], synthetic['on_time_pct'], synthetic['median_cycle_days']) == (2026, 5000, 96.72, 5.07))
        check('Synthetic late cases', round(synthetic['case_count'] * (100-synthetic['on_time_pct'])/100) == 164)
        if expected_synthetic:
            check('Synthetic CSV exact recovered bytes', sha(run_dir / 'outputs/part2/synthetic_returns_cases.csv') == sha(expected_synthetic))
        else:
            report['synthetic_file_comparison'] = 'NOT RUN: no saved synthetic CSV supplied'
        report['database_sha256'] = before
        report['status'] = 'PASS'
    except Exception as exc:
        report['status'] = 'FAIL'
        report['error'] = str(exc)
        raise
    finally:
        target.write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: ' + str(target))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--saved-validation', type=Path)
    parser.add_argument('--expected-synthetic', type=Path)
    args = parser.parse_args()
    verify(args.run_dir, args.saved_validation, args.expected_synthetic)
