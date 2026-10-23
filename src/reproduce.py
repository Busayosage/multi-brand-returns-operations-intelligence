"""Run recovered stages in a NEW isolated directory; never overwrite a baseline."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = [
    ('resolve_cross_sheet_duplicates', 'cross_sheet_', 'transactions_after_cross_sheet_matching.csv'),
    ('flag_missing_customer_ids', 'customer_id_', 'transactions_with_customer_id_flag.csv'),
    ('flag_missing_descriptions', 'description_', 'transactions_with_description_flag.csv'),
    ('flag_price_exceptions', 'price_', 'transactions_with_price_flags.csv'),
    ('classify_transaction_patterns', 'transaction_patterns_', 'transactions_with_pattern_classification.csv'),
    ('correct_bad_debt_classification', 'bad_debt_correction_', 'transactions_with_corrected_accounting.csv'),
    ('classify_stock_codes', 'stock_codes_', 'transactions_with_stock_code_categories.csv'),
]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def run(input_path, run_dir):
    input_path, run_dir = input_path.resolve(), run_dir.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    run_dir.mkdir(parents=True, exist_ok=False)
    outputs = run_dir / 'outputs'
    outputs.mkdir()
    evidence = {'status': 'RUNNING', 'python': platform.python_version(),
                'input_sha256': sha(input_path), 'stages': []}
    manifest = run_dir / 'run_manifest.json'

    def save():
        manifest.write_text(json.dumps(evidence, indent=2) + '\n')

    def stage(name, args, prefix=None):
        before = set(outputs.iterdir())
        started = time.monotonic()
        print('Running ' + name, flush=True)
        command = [sys.executable, str(ROOT / 'src' / (name + '.py')), *map(str, args)]
        with (run_dir / (name + '.log')).open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        record = {'stage': name, 'exit_code': result.returncode,
                  'elapsed_seconds': round(time.monotonic() - started, 2)}
        evidence['stages'].append(record)
        save()
        if result.returncode:
            raise RuntimeError(name + ' failed; inspect its log in ' + str(run_dir))
        if prefix:
            new = [p for p in set(outputs.iterdir()) - before if p.name.startswith(prefix)]
            if len(new) != 1:
                raise RuntimeError('Expected one new output directory for ' + name)
            record['output_directory'] = str(new[0].relative_to(run_dir))
            save()
            return new[0]

    save()
    try:
        source = input_path
        for name, prefix, filename in STAGES:
            folder = stage(name, ['--input', source, '--output', outputs], prefix)
            source = folder / filename
        quality = stage('build_quality_review', ['--input', source, '--output', outputs], 'quality_review_')
        eligibility = stage('define_kpi_eligibility', ['--input', source, '--review', quality / 'quality_review_summary.json', '--output', outputs], 'kpi_eligibility_')
        source = eligibility / 'transactions_with_kpi_eligibility.csv'
        kpis = stage('calculate_kpis', ['--input', source, '--output', outputs], 'kpis_')
        reviewed = stage('review_invoice_keys', ['--input', source, '--prior-kpis', kpis, '--output', outputs], 'invoice_review_')
        database = run_dir / 'database' / 'retail_analytics.db'
        stage('import_to_sqlite', ['--input', source, '--review-dir', reviewed, '--database', database])
        export = stage('export_dashboard_data', ['--database', database, '--output-root', outputs], 'dashboard_export_')
        stage('part2_returns_intelligence', ['--db', database, '--output-dir', outputs / 'part2', '--count', 5000, '--seed', 2026])
        evidence['database_sha256'] = sha(database)
        evidence['dashboard_export'] = str(export.relative_to(run_dir))
        evidence['input_unchanged'] = sha(input_path) == evidence['input_sha256']
        if not evidence['input_unchanged']:
            raise RuntimeError('Source workbook changed during run')
        evidence['status'] = 'PASS'
    except Exception as exc:
        evidence['status'] = 'FAIL'
        evidence['error'] = str(exc)
        raise
    finally:
        save()
    print('PASS: ' + str(manifest), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, required=True, help='Must not exist; retains all audits and logs')
    args = parser.parse_args()
    run(args.input, args.run_dir)
