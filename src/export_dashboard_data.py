"""Export the reviewed retail database for Tableau and Power BI.

Save in src/export_dashboard_data.py. Uses Python's standard library only.
Reads SQLite in read-only mode; creates a new timestamped output directory.
"""
import argparse
import csv
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGG = '''SELECT COUNT(*) AS rows,
 SUM(sales_eligible) AS sales_lines,
 SUM(cancellation_eligible) AS cancellation_lines,
 SUM(customer_sales_eligible) AS customer_sales_lines,
 SUM(gross_units) AS gross_units,
 SUM(cancellation_units) AS cancellation_units,
 COUNT(DISTINCT CASE WHEN sales_eligible=1 THEN invoice_key END) AS orders,
 COUNT(DISTINCT CASE WHEN customer_sales_eligible=1 THEN customer_key END) AS customers
 FROM analysis_transactions'''
JOIN = ''' FROM source_transactions s
 JOIN analysis_transactions a ON a.source_row_id=s.Source_Row_ID'''
SELECT = '''SELECT s.*, a.invoice_key, a.customer_key, a.month,
 a.sales_eligible, a.cancellation_eligible, a.customer_sales_eligible,
 a.gross_units, a.cancellation_units'''
EXTRA = ['transaction_date', 'comparable_jan_nov', 'reviewed_pair',
         'gross_merchandise_gbp', 'cancellation_marked_gbp',
         'net_recorded_merchandise_gbp']
PAIR = {'Year 2010-2011!61621', 'Year 2010-2011!61626'}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def hash_row(h, values):
    h.update((json.dumps(values, ensure_ascii=False, separators=(',', ':')) + '\n').encode())


def bucket():
    return dict(rows=0, sales_lines=0, cancellation_lines=0,
                customer_sales_lines=0, gross_units=0, cancellation_units=0,
                orders=set(), customers=set())


def add(b, r):
    b['rows'] += 1
    for target, field in [('sales_lines', 'sales_eligible'),
                          ('cancellation_lines', 'cancellation_eligible'),
                          ('customer_sales_lines', 'customer_sales_eligible'),
                          ('gross_units', 'gross_units'),
                          ('cancellation_units', 'cancellation_units')]:
        b[target] += int(r[field])
    if r['sales_eligible'] == '1':
        b['orders'].add(r['invoice_key'])
    if r['customer_sales_eligible'] == '1':
        b['customers'].add(r['customer_key'])


def finish(b):
    return {k: len(v) if isinstance(v, set) else v for k, v in b.items()}


def export(database, output_root):
    database = database.resolve()
    need(database.is_file(), 'Database not found: ' + str(database))
    con = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    out = None
    try:
        con.execute('PRAGMA query_only=ON')
        con.execute('BEGIN')  # All reads use the same database snapshot.
        metadata = dict(con.execute('SELECT key,value FROM import_metadata'))
        need(metadata.get('validation', '').startswith('Passed:'), 'Missing successful import validation.')
        scale = int(metadata['money_scale'])
        need(scale > 0 and str(scale)[0] == '1' and set(str(scale)[1:]) <= {'0'},
             'Money scale must be a power of ten.')
        places = len(str(scale)) - 1
        money = lambda units: format(Decimal(units) / scale, f'.{places}f')
        expected = {'ALL': dict(con.execute(AGG).fetchone())}
        need(expected['ALL']['rows'] > 0, 'Database has no analysis rows.')
        expected.update({'MONTH:' + r['month']: {k: r[k] for k in expected['ALL']}
                         for r in con.execute(AGG.replace('SELECT ', 'SELECT month, ', 1) + ' GROUP BY month')})
        for year in ('2010', '2011'):
            expected['JAN_NOV:' + year] = dict(con.execute(
                AGG + ' WHERE month BETWEEN ? AND ?', (year+'-01', year+'-11')).fetchone())
        expected = {key: {k: (v if v is not None else 0) for k, v in row.items()}
                    for key, row in expected.items()}
        n = expected['ALL']['rows']
        need(con.execute('SELECT COUNT(*) FROM source_transactions').fetchone()[0] == n,
             'Source and analysis row counts differ.')
        for table, key in [('source_transactions', 'Source_Row_ID'), ('analysis_transactions', 'source_row_id')]:
            need(con.execute(f'SELECT COUNT(DISTINCT {key}) FROM {table}').fetchone()[0] == n,
                 'Missing or duplicate source keys.')
        need(con.execute('SELECT COUNT(*)' + JOIN).fetchone()[0] == n, 'Join loses or multiplies rows.')
        statuses = dict(con.execute('SELECT KPI_Eligibility_Status, COUNT(*) FROM source_transactions GROUP BY KPI_Eligibility_Status'))
        cursor = con.execute(SELECT + JOIN + ' ORDER BY s.rowid')
        base = [c[0] for c in cursor.description]
        headers = base + EXTRA
        need(len({h.lower() for h in headers}) == len(headers), 'Export field name collision.')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        out = output_root.resolve() / ('dashboard_export_' + stamp)
        out.mkdir(parents=True, exist_ok=False)
        data = out / 'dashboard_transactions.csv'
        original = hashlib.sha256()
        print('Exporting all retained transaction lines...', flush=True)
        with data.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for i, row in enumerate(cursor, 1):
                r = dict(row)
                date = datetime.fromisoformat(r['InvoiceDate']).date().isoformat()
                need(date[:7] == r['month'], 'Invoice date and analytical month differ.')
                comparable = int('2010-01' <= r['month'] <= '2010-11' or '2011-01' <= r['month'] <= '2011-11')
                vals = [str(r[k]) for k in base] + [date, str(comparable),
                    str(int(r['Source_Row_ID'] in PAIR)), money(r['gross_units']),
                    money(r['cancellation_units']), money(r['gross_units']-r['cancellation_units'])]
                writer.writerow(vals)
                hash_row(original, vals)
                if i % 200000 == 0:
                    print(f'  Exported {i:,} rows', flush=True)
        print('Reading the CSV back and reconciling exact KPIs...', flush=True)
        actual = {k: bucket() for k in expected}
        seen_statuses = Counter()
        readback = hashlib.sha256()
        with data.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            need(reader.fieldnames == headers, 'CSV header mismatch.')
            for r in reader:
                hash_row(readback, [r[k] for k in headers])
                add(actual['ALL'], r)
                add(actual['MONTH:' + r['month']], r)
                if r['comparable_jan_nov'] == '1':
                    add(actual['JAN_NOV:' + r['month'][:4]], r)
                seen_statuses[r['KPI_Eligibility_Status']] += 1
        need(readback.digest() == original.digest(), 'CSV field readback mismatch.')
        actual = {k: finish(b) for k, b in actual.items()}
        need(actual == expected, 'Export KPIs differ from SQLite.')
        need(dict(seen_statuses) == statuses, 'Export status counts differ from SQLite.')
        reference = out / 'kpi_reference.csv'
        with reference.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['scope'] + list(expected['ALL']))
            writer.writeheader()
            for scope, values in expected.items():
                writer.writerow(dict(scope=scope, **values))
        guide = out / 'README_dashboard.md'
        guide.write_text('''# Dashboard export — Tableau and Power BI

Use dashboard_transactions.csv as the transaction data source. One row is one
retained source line. All original fields and flags are included unchanged.
Do not join kpi_reference.csv to it: that file is for independent KPI checks.

## Types and calculations
- Set Source_Row_ID, Invoice, invoice_key, Customer ID, customer_key and
  StockCode to TEXT before analysis (preserve leading zeros).
- transaction_date is an ISO date; InvoiceDate retains the source timestamp.
- month is YYYY-MM text. comparable_jan_nov=1 selects Jan–Nov 2010 and 2011.
- gross_units and cancellation_units are exact scaled integer money, not quantities.
- GBP fields retain full source precision. Sum first; format totals to two decimals.
- Sales orders: distinct invoice_key WHERE sales_eligible=1.
- Identified purchasing customers: distinct customer_key WHERE customer_sales_eligible=1.
- AOV: SUM(gross_merchandise_gbp) / distinct eligible sales orders.
- Net: SUM(gross_merchandise_gbp) - SUM(cancellation_marked_gbp).
- Cancellation-value ratio: 100 * SUM(cancellation_marked_gbp) / SUM(gross_merchandise_gbp).
  Return null when a denominator is zero. Never average row-level ratios or monthly AOVs.
- Original source flags are True/False text; analytical eligibility fields are 0/1 integers.
- For country comparisons, trim Country and group blanks as [Unknown].
- Blank customer IDs are an unknown group, never one identified customer.
- Group products by StockCode: descriptions can vary within a product.

## Scope
All retained lines and repeated rows remain. Non-eligible amounts contribute zero
to the monetary KPIs. Do not globally filter to sales only: that would remove cancellations.
Keep reviewed_pair=1 in headline reporting; exclude only for labelled sensitivity.
December 2011 is partial (source ends 9 December). Use comparable_jan_nov=1 for YoY.
Cancellation-marked value is not confirmed physical returns. Net value is not profit.
Eligibility policy remains provisional. No brand or logistics fields are invented.
CSV files contain no enforced types; check types and KPI totals after each BI import.
The validation report checks this export against SQLite, not against the raw workbook.
''', encoding='utf-8')
        report = {'status': 'PASS', 'database': str(database), 'import_metadata': metadata,
                  'money_scale': scale, 'rows': n, 'monthly_scopes_checked': len(expected)-3,
                  'exact_kpis': actual, 'eligibility_status_counts': statuses,
                  'all_exported_fields_readback_match': True,
                  'source_database_modified': False,
                  'script_sha256': sha(Path(__file__)),
                  'output_sha256': {p.name: sha(p) for p in (data, reference, guide)}}
        (out/'validation_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(f'Exported rows: {n:,}\nAll exported fields: MATCH\nOverall, monthly and Jan-Nov KPIs: MATCH\nValidation: PASS\nOutputs: {out}')
        return out
    except Exception as exc:
        if out is not None:
            (out/'FAILED.txt').write_text('DO NOT USE THIS EXPORT.\n' + str(exc), encoding='utf-8')
        raise
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=ROOT/'database/retail_analytics.db')
    parser.add_argument('--output-root', type=Path, default=ROOT/'outputs')
    args = parser.parse_args()
    export(args.database, args.output_root)


if __name__ == '__main__':
    main()
