r"""Load the reviewed retail snapshot into SQLite without changing source fields.
Run from VS Code: .\.venv\Scripts\python.exe src\import_to_sqlite.py
Standard library only. Existing databases must contain no user tables/views.
"""
import argparse
import csv
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'outputs/kpi_eligibility_20260917T012349887393Z/transactions_with_kpi_eligibility.csv'
REVIEW = ROOT / 'outputs/invoice_review_20260917T014004949966Z'
LIMIT = 2**63 - 1

def need(condition, message):
    if not condition:
        raise ValueError(message)

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def rows(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        yield from csv.DictReader(f)

def quote(s):
    return '"' + s.replace('"', '""') + '"'

def flag(s):
    need(s in ('True', 'False'), 'Unexpected boolean value: ' + repr(s))
    return int(s == 'True')

def row_hash(h, values):
    h.update((json.dumps(values, ensure_ascii=False, separators=(',', ':'))+'\n').encode())

def display(n):
    return format(n.quantize(Decimal('.01'), rounding=ROUND_HALF_UP), '.2f')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=INPUT)
    parser.add_argument('--review-dir', type=Path, default=REVIEW)
    parser.add_argument('--database', type=Path, default=ROOT/'database/retail_analytics.db')
    args = parser.parse_args()
    source, review, target = args.input.resolve(), args.review_dir.resolve(), args.database.resolve()
    parent_path = source.with_name('kpi_eligibility_summary.json')
    review_path = review/'invoice_review_summary.json'
    overall_path, monthly_path = review/'kpi_overall_reviewed.csv', review/'kpi_monthly_reviewed.csv'
    tracked = [source, parent_path, review_path, overall_path, monthly_path]
    hashes = {str(p): sha(p) for p in tracked}
    parent = json.loads(parent_path.read_text(encoding='utf-8'))
    reviewed = json.loads(review_path.read_text(encoding='utf-8'))
    need(hashes[str(source)] == parent['output_sha256'], 'Source differs from eligibility summary.')
    need(hashes[str(source)] in reviewed['input_hashes'].values(), 'Invoice review is for a different source.')
    need(reviewed['remaining_invoice_keys_requiring_review'] == 0, 'Invoice review is unresolved.')
    for p in (overall_path, monthly_path):
        need(hashes[str(p)] == reviewed['output_hashes'][p.name], 'Reviewed report checksum mismatch.')
    with source.open(newline='', encoding='utf-8-sig') as f:
        headers = next(csv.reader(f))
    need(len(set(x.lower() for x in headers)) == len(headers), 'Duplicate column names.')
    print('Checking exact monetary scale...', flush=True)
    places = 0
    count = 0
    for r in rows(source):
        count += 1
        if flag(r['Sales_KPI_Eligible']) or flag(r['Cancellation_KPI_Eligible']):
            p, q = Decimal(r['Price']), Decimal(r['Quantity'])
            need(p.is_finite() and p > 0 and q.is_finite() and q == q.to_integral_value(), 'Invalid eligible amount.')
            places = max(places, -p.as_tuple().exponent)
    need(count == parent['output_rows'] == reviewed['input_rows'], 'Row count mismatch.')
    need(places <= 9, 'Unexpected monetary scale; review before import.')
    scale = 10**places
    target.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(target, timeout=5)
    original_hash = hashlib.sha256()
    absolute_total = 0
    try:
        con.execute('BEGIN EXCLUSIVE')
        need(not con.execute("SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall(),
             'Database already has objects. No overwrite performed; use a new --database path.')
        definitions = [quote(c)+' TEXT NOT NULL'+(' PRIMARY KEY' if c == 'Source_Row_ID' else '') for c in headers]
        con.execute('CREATE TABLE source_transactions (' + ','.join(definitions) + ')')
        con.execute('''CREATE TABLE analysis_transactions (
          source_row_id TEXT PRIMARY KEY REFERENCES source_transactions(Source_Row_ID),
          invoice_key TEXT NOT NULL, customer_key TEXT NOT NULL, month TEXT NOT NULL,
          sales_eligible INTEGER NOT NULL CHECK(sales_eligible IN (0,1)),
          cancellation_eligible INTEGER NOT NULL CHECK(cancellation_eligible IN (0,1)),
          customer_sales_eligible INTEGER NOT NULL CHECK(customer_sales_eligible IN (0,1)),
          gross_units INTEGER NOT NULL, cancellation_units INTEGER NOT NULL,
          CHECK(sales_eligible+cancellation_eligible<=1))''')
        raw_batch, analytical_batch = [], []
        insert = 'INSERT INTO source_transactions VALUES ('+','.join('?' for _ in headers)+')'
        print('Loading retained rows...', flush=True)
        for i, r in enumerate(rows(source), 1):
            vals = [r[c] for c in headers]
            row_hash(original_hash, vals)
            s, c, cs = (flag(r[k]) for k in ('Sales_KPI_Eligible','Cancellation_KPI_Eligible','Customer_Sales_KPI_Eligible'))
            need(not (s and c) and cs <= s, 'Inconsistent eligibility flags.')
            gross = cancel = 0
            if s or c:
                exact = Decimal(r['Quantity']) * Decimal(r['Price']) * scale
                need(exact == exact.to_integral_value(), 'Monetary precision loss.')
                need((s and exact > 0) or (c and exact < 0), 'Unexpected eligible sign.')
                gross, cancel = (int(exact), 0) if s else (0, -int(exact))
                absolute_total += gross + cancel
                need(absolute_total <= LIMIT, 'SQLite integer overflow risk.')
            raw_batch.append(vals)
            analytical_batch.append((r['Source_Row_ID'],r['Invoice'].strip().upper(),r['Customer ID'].strip(),r['InvoiceDate'][:7],s,c,cs,gross,cancel))
            if i % 10000 == 0:
                con.executemany(insert, raw_batch)
                con.executemany('INSERT INTO analysis_transactions VALUES (?,?,?,?,?,?,?,?,?)', analytical_batch)
                raw_batch.clear(); analytical_batch.clear()
                if i % 200000 == 0:
                    print(f'  Loaded {i:,} rows', flush=True)
        con.executemany(insert, raw_batch)
        con.executemany('INSERT INTO analysis_transactions VALUES (?,?,?,?,?,?,?,?,?)', analytical_batch)
        con.execute('CREATE TABLE import_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        con.executemany('INSERT INTO import_metadata VALUES (?,?)', [('money_scale',str(scale)),('source_sha256',hashes[str(source)]),('policy','Provisional merchandise v1.0; invoice proxy rule v1.1')])
        con.execute('CREATE INDEX ix_analysis_month ON analysis_transactions(month)')
        con.execute('CREATE INDEX ix_analysis_invoice ON analysis_transactions(invoice_key)')
        aggregate = '''SELECT SUM(sales_eligible) AS Sales_Lines,
          SUM(cancellation_eligible) AS Cancellation_Lines,
          SUM(gross_units) AS Gross_Units, SUM(cancellation_units) AS Cancellation_Units,
          COUNT(DISTINCT CASE WHEN sales_eligible=1 THEN invoice_key END) AS Sales_Orders,
          COUNT(DISTINCT CASE WHEN customer_sales_eligible=1 THEN customer_key END) AS Identified_Purchasing_Customers,
          SUM(customer_sales_eligible) AS Customer_Linked_Sales_Lines FROM analysis_transactions'''
        con.execute('CREATE VIEW kpi_overall_exact AS '+aggregate)
        con.execute('CREATE VIEW kpi_monthly_exact AS '+aggregate.replace('SELECT ', 'SELECT month AS Month, ',1)+' GROUP BY month')
        con.row_factory = sqlite3.Row
        def reconcile(actual, expected):
            for k in ('Sales_Lines','Cancellation_Lines','Sales_Orders','Identified_Purchasing_Customers','Customer_Linked_Sales_Lines'):
                need(actual[k] == int(expected[k]), 'KPI mismatch: '+k)
            g, c = Decimal(actual['Gross_Units'])/scale, Decimal(actual['Cancellation_Units'])/scale
            need(g == Decimal(expected['Gross_Value_Exact']) and c == Decimal(expected['Cancellation_Value_Exact']), 'Exact money mismatch.')
            for k, val in [('Gross_Merchandise_Value',g),('Cancellation_Marked_Value',c),('Net_Recorded_Merchandise_Value',g-c)]:
                need(display(val) == expected[k], 'Displayed money mismatch: '+k)
            if actual['Sales_Orders']:
                need(display(g/actual['Sales_Orders']) == expected['Average_Merchandise_Order_Value'], 'AOV mismatch.')
        overall = dict(con.execute('SELECT * FROM kpi_overall_exact').fetchone())
        reconcile(overall, next(rows(overall_path)))
        monthly = {r['Month']: dict(r) for r in con.execute('SELECT * FROM kpi_monthly_exact')}
        expected_months = {r['Month']: r for r in rows(monthly_path)}
        need(monthly.keys() == expected_months.keys(), 'Monthly coverage mismatch.')
        for month, r in monthly.items():
            reconcile(r, expected_months[month])
        actual_statuses = dict(con.execute('SELECT KPI_Eligibility_Status, COUNT(*) FROM source_transactions GROUP BY KPI_Eligibility_Status'))
        need(actual_statuses == parent['status_counts'], 'Status count mismatch.')
        print('Checking every imported source field...', flush=True)
        stored_hash = hashlib.sha256()
        for r in con.execute('SELECT '+','.join(quote(c) for c in headers)+' FROM source_transactions ORDER BY rowid'):
            row_hash(stored_hash, list(r))
        need(stored_hash.digest() == original_hash.digest(), 'Source field readback mismatch.')
        need(con.execute('SELECT COUNT(*) FROM analysis_transactions').fetchone()[0] == count, 'Analytical row count mismatch.')
        need(not con.execute('PRAGMA foreign_key_check').fetchall(), 'Broken provenance link.')
        need(con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Database integrity check failed.')
        need(all(sha(p) == hashes[str(p)] for p in tracked), 'An input changed during import.')
        con.execute("INSERT INTO import_metadata VALUES ('validation','Passed: all source fields, counts, overall and monthly reviewed KPIs')")
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    report = target.parent / ('sqlite_import_'+stamp+'.json')
    report.write_text(json.dumps({'status':'Validated','rows':count,'money_scale':scale,'database':str(target),'database_sha256':sha(target),'script_sha256':sha(Path(__file__)),'input_hashes':hashes,'overall_exact':overall,'months_reconciled':len(monthly),'source_fields_preserved':True,'scope':'Provisional merchandise metrics; cancellation-marked value is not confirmed physical returns; orders are invoice proxies.'},indent=2),encoding='utf-8')
    print(f'Imported rows: {count:,}\nExact money scale: {scale}\nOverall and {len(monthly)} monthly KPI reports: MATCH\nAll source fields and flags: PRESERVED\nDatabase: {target}\nValidation report: {report}')

if __name__ == '__main__':
    main()
