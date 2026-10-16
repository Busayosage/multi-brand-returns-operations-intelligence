"""Part 2: observed cancellations + entirely separate synthetic logistics demo.

Standard library only. Reads the recovered UCI Retail II SQLite database in read-only
mode. It never edits underlying transactions or treats cancellation as physical return.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median, mean

PAIRS = ("Year 2010-2011!61621", "Year 2010-2011!61626")
SCALE = 1000
SYNTHETIC_FIELDS = (
    "synthetic_case_id", "provenance", "requested_at", "carrier_label",
    "warehouse_label", "requested_service", "handover_at", "warehouse_scan_at",
    "inspection_completed_at", "resolution_at", "sla_days", "modelled_processing_cost_gbp",
)


def money(units: int) -> float:
    return round(units / SCALE, 3)


def percentage(numerator: int, denominator: int) -> float | None:
    return round(numerator * 100.0 / denominator, 2) if denominator else None


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def observed_analysis(db_path: Path) -> dict:
    """Aggregate eligible source transactions without changing the database."""
    if not db_path.is_file():
        raise FileNotFoundError(db_path)
    connection = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Database quick_check failed")
        total_rows = connection.execute("SELECT COUNT(*) FROM source_transactions").fetchone()[0]
        if total_rows != connection.execute("SELECT COUNT(*) FROM analysis_transactions").fetchone()[0]:
            raise ValueError("Unreconciled source versus analysis row counts")
        query = """
        SELECT SUBSTR(month, 1, 4) AS year,
               SUM(sales_eligible) AS sales_lines,
               SUM(cancellation_eligible) AS cancellation_lines,
               SUM(gross_units) AS gross_units,
               SUM(cancellation_units) AS cancelled_units
        FROM analysis_transactions
        WHERE month BETWEEN '2010-01' AND '2010-11'
           OR month BETWEEN '2011-01' AND '2011-11'
        GROUP BY SUBSTR(month, 1, 4)
        ORDER BY year
        """
        years = {}
        for row in connection.execute(query):
            gross, cancel = int(row["gross_units"]), int(row["cancelled_units"])
            years[row["year"]] = {
                "gross_merchandise_gbp": money(gross),
                "cancellation_marked_gbp": money(cancel),
                "net_recorded_merchandise_gbp": money(gross - cancel),
                "cancellation_value_ratio_pct": percentage(cancel, gross),
                "sales_eligible_lines": row["sales_lines"],
                "cancellation_eligible_lines": row["cancellation_lines"],
            }
        if set(years) != {"2010", "2011"}:
            raise ValueError("Missing 2010 or 2011 comparison period")
        pair_query = """
        SELECT a.source_row_id, a.gross_units, a.cancellation_units,
               s.Invoice, s.StockCode, s.Quantity, s.Price, s.InvoiceDate, s."Customer ID"
        FROM analysis_transactions AS a
        JOIN source_transactions AS s ON s.Source_Row_ID = a.source_row_id
        WHERE a.source_row_id IN (?, ?)
        ORDER BY s.InvoiceDate
        """
        pair = [dict(row) for row in connection.execute(pair_query, PAIRS)]
        if len(pair) != 2:
            raise ValueError("Reviewed-pair source rows missing")
        sale, reversal = pair
        pair_matches = (
            sale["StockCode"] == reversal["StockCode"]
            and sale["Customer ID"] == reversal["Customer ID"]
            and sale["Price"] == reversal["Price"]
            and int(sale["Quantity"]) == -int(reversal["Quantity"])
            and int(sale["gross_units"]) == int(reversal["cancellation_units"]) > 0
            and int(sale["cancellation_units"]) == int(reversal["gross_units"]) == 0
        )
        if not pair_matches:
            raise ValueError("Reviewed-pair matching conditions not met")
        elapsed = (datetime.fromisoformat(reversal["InvoiceDate"]) -
                   datetime.fromisoformat(sale["InvoiceDate"])).total_seconds() / 60
        pair_value_units = int(sale["gross_units"])
        if elapsed < 0:
            raise ValueError("Reviewed pair has reversed chronology")
        sensitivity = connection.execute("""
        SELECT SUM(gross_units) AS gross_units,
               SUM(cancellation_units) AS cancelled_units,
               SUM(cancellation_eligible) AS cancellation_lines
        FROM analysis_transactions
        WHERE month BETWEEN '2011-01' AND '2011-11'
          AND source_row_id NOT IN (?, ?)
        """, PAIRS).fetchone()
        sgross, scancel = int(sensitivity["gross_units"]), int(sensitivity["cancelled_units"])
        if money(sgross - scancel) != years["2011"]["net_recorded_merchandise_gbp"]:
            raise ValueError("Excluding the reviewed offsetting pair changed net value")
        product_row = connection.execute("""
        SELECT s.StockCode AS product_code, MIN(s.Description) AS example_description,
               SUM(a.cancellation_units) AS marked_units,
               SUM(a.cancellation_eligible) AS marked_lines
        FROM analysis_transactions AS a
        JOIN source_transactions AS s ON s.Source_Row_ID = a.source_row_id
        WHERE a.month BETWEEN '2011-01' AND '2011-11'
          AND (a.sales_eligible = 1 OR a.cancellation_eligible = 1)
        GROUP BY s.StockCode
        HAVING SUM(a.cancellation_units) > 0
        ORDER BY marked_units DESC
        LIMIT 1
        """).fetchone()
        yearly_pct_change = percentage(
            int(round(years["2011"]["cancellation_marked_gbp"] * 1000)) -
            int(round(years["2010"]["cancellation_marked_gbp"] * 1000)),
            int(round(years["2010"]["cancellation_marked_gbp"] * 1000)),
        )
        return {
            "source": "Public UCI Online Retail II; local recovered SQLite snapshot",
            "analysis_window": "Comparable January-November 2010 and 2011",
            "model_policy": "Provisional eligible merchandise policy; value in integer GBP thousandths",
            "source_transaction_rows": total_rows,
            "database_sha256": sha256_of_file(db_path),
            "periods": years,
            "cancellation_marked_value_change_pct": yearly_pct_change,
            "cancellation_line_count_change_pct": percentage(
                years["2011"]["cancellation_eligible_lines"] - years["2010"]["cancellation_eligible_lines"],
                years["2010"]["cancellation_eligible_lines"]),
            "largest_2011_product_cancel_value": {
                "stock_code": product_row["product_code"],
                "example_description": product_row["example_description"],
                "cancellation_marked_gbp": money(int(product_row["marked_units"])),
                "cancellation_eligible_lines": int(product_row["marked_lines"]),
                "share_of_2011_cancel_value_pct": percentage(
                    int(product_row["marked_units"]),
                    int(round(years["2011"]["cancellation_marked_gbp"] * 1000))),
            },
            "reviewed_offsetting_pair": {
                "source_row_ids": list(PAIRS),
                "product_code": sale["StockCode"],
                "quantity_each_direction": abs(int(sale["Quantity"])),
                "value_each_direction_gbp": money(pair_value_units),
                "elapsed_minutes": elapsed,
                "share_of_2011_cancel_value_pct": percentage(
                    pair_value_units, int(round(years["2011"]["cancellation_marked_gbp"] * 1000))),
                "interpretation": "Matched candidate reversal; not a confirmed return, error or refund",
            },
            "2011_pair_exclusion_sensitivity_only": {
                "gross_merchandise_gbp": money(sgross),
                "cancellation_marked_gbp": money(scancel),
                "net_recorded_merchandise_gbp": money(sgross - scancel),
                "cancellation_value_ratio_pct": percentage(scancel, sgross),
                "cancellation_eligible_lines": int(sensitivity["cancellation_lines"]),
                "caveat": "Illustrative exclusion of BOTH reviewed rows, not a corrected KPI. Headline remains 3.23%.",
            },
            "limitation": "Cancellation prefixes do not prove physical returns, transit, refunds, warehouse or carrier performance.",
        }
    finally:
        connection.close()


def generate_synthetic_cases(count: int, seed: int) -> list[dict]:
    """Independent imaginary returns operation; NO linking to source transactions."""
    if count < 1 or count > 100_000:
        raise ValueError("--count must be in [1, 100000]")
    rng = random.Random(seed)
    base = datetime(2026, 1, 1, 8)
    cases = []
    carrier_values = ("Carrier A", "Carrier B", "Carrier C")
    hub_values = ("Hub North", "Hub Central", "Hub South")
    # Hypothetical routing/service assumptions, NOT measured performance.
    transit_base_days = {"Carrier A": 1.6, "Carrier B": 2.3, "Carrier C": 2.9}
    inspection_base_days = {"Hub North": 0.55, "Hub Central": 0.9, "Hub South": 1.25}
    for i in range(count):
        requested = base + timedelta(days=rng.randrange(180),hours=rng.randrange(0,12),minutes=rng.randrange(60))
        carrier = rng.choices(carrier_values, weights=(42,35,23), k=1)[0]
        warehouse = rng.choices(hub_values, weights=(32,40,28), k=1)[0]
        service = rng.choices(("Standard", "Priority"), weights=(80,20), k=1)[0]
        handover_days = max(0.15, rng.gauss(0.8,0.25))
        transit_days = max(0.4, rng.gauss(transit_base_days[carrier],0.65))
        if requested.weekday() >= 4:
            transit_days += 0.7  # Deliberate simulated late-week effect
        inspection_days = max(0.2, rng.gauss(inspection_base_days[warehouse],0.4))
        resolution_days = max(0.1, rng.gauss(0.9,0.3))
        handover = requested + timedelta(days=handover_days)
        warehouse_scan = handover + timedelta(days=transit_days)
        inspected = warehouse_scan + timedelta(days=inspection_days)
        resolved = inspected + timedelta(days=resolution_days)
        cost = round(3.0 + 1.7*transit_days + 2.8*inspection_days + 1.1*resolution_days,2)
        cases.append({
            "synthetic_case_id": f"SIM-{i+1:06d}", "provenance": "SYNTHETIC_ONLY",
            "requested_at": requested.isoformat(timespec="seconds"),
            "carrier_label": carrier, "warehouse_label": warehouse,
            "requested_service": service,
            "handover_at": handover.isoformat(timespec="seconds"),
            "warehouse_scan_at": warehouse_scan.isoformat(timespec="seconds"),
            "inspection_completed_at": inspected.isoformat(timespec="seconds"),
            "resolution_at": resolved.isoformat(timespec="seconds"),
            "sla_days": 7,
            "modelled_processing_cost_gbp": cost,
        })
    return cases


def synthetic_summary(cases: list[dict], seed: int) -> dict:
    seen, durations, by_carrier, by_hub, by_request_weekday = set(), [], defaultdict(list), defaultdict(list), defaultdict(list)
    for case in cases:
        if case["provenance"] != "SYNTHETIC_ONLY":
            raise ValueError("Non-synthetic row in synthetic scenario")
        case_id = case["synthetic_case_id"]
        if case_id in seen:
            raise ValueError("Duplicate synthetic case ID")
        seen.add(case_id)
        timestamps = [datetime.fromisoformat(case[k]) for k in
                      ("requested_at","handover_at","warehouse_scan_at","inspection_completed_at","resolution_at")]
        if timestamps != sorted(timestamps):
            raise ValueError("Invalid chronological order")
        cycle_days = (timestamps[-1] - timestamps[0]).total_seconds() / 86400
        if cycle_days < 0 or case["sla_days"] <= 0:
            raise ValueError("Invalid lifecycle/SLA")
        durations.append(cycle_days)
        is_on_time = cycle_days <= case["sla_days"]
        by_carrier[case["carrier_label"]].append(is_on_time)
        by_hub[case["warehouse_label"]].append(is_on_time)
        by_request_weekday[timestamps[0].strftime("%A")].append(is_on_time)
    def group_summary(groups):
        return {key:{"cases":len(values),"on_time_pct":percentage(sum(values),len(values))}
                for key,values in sorted(groups.items())}
    ordered = sorted(durations)
    n = len(ordered)
    return {
        "provenance": "SYNTHETIC_ONLY — no source invoice/customer/cancellation links",
        "seed": seed,"case_count": n,"sla_target_days": 7,
        "on_time_pct": percentage(sum(d<=7 for d in durations),n),
        "median_cycle_days": round(median(durations),2),
        "mean_cycle_days": round(mean(durations),2),
        "p90_cycle_days": round(ordered[max(0, -1 + int(n*0.90+0.999999))],2),
        "by_carrier": group_summary(by_carrier),
        "by_warehouse": group_summary(by_hub),
        "by_requested_weekday": group_summary(by_request_weekday),
        "assumptions": "Hypothetical carrier/hub delays and Friday-Sunday uplift were coded into the generator. They are not detected real bottlenecks, SLAs or costs.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db",type=Path,required=True,help="Local SQLite retail_analytics.db (read-only)")
    parser.add_argument("--output-dir",type=Path,default=Path("outputs/part2"))
    parser.add_argument("--count",type=int,default=5000)
    parser.add_argument("--seed",type=int,default=2026)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    observed = observed_analysis(args.db)
    synthetic = generate_synthetic_cases(args.count,args.seed)
    simulation = synthetic_summary(synthetic,args.seed)
    with (args.output_dir/"synthetic_returns_cases.csv").open("w",newline="",encoding="utf-8") as file:
        writer = csv.DictWriter(file,fieldnames=SYNTHETIC_FIELDS)
        writer.writeheader()
        writer.writerows(synthetic)
    report = {
        "project":"Multi-Brand Returns Operations Intelligence",
        "part":"Part 2 — Cancellation Exceptions and Simulated Logistics",
        "observed_transaction_analysis":observed,
        "entirely_separate_synthetic_logistics_scenario":simulation,
        "publication_caveat":"Real cancellation figures and synthetic logistics KPIs are unrelated; never present the latter as actual operational outcomes.",
    }
    destination = args.output_dir/"part2_results.json"
    destination.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"saved_report":str(destination),"synthetic_cases":len(synthetic),
                      "2011_cancellation_value_ratio_pct":observed["periods"]["2011"]["cancellation_value_ratio_pct"],
                      "2011_pair_exclusion_sensitivity_pct":observed["2011_pair_exclusion_sensitivity_only"]["cancellation_value_ratio_pct"],
                      "synthetic_on_time_pct":simulation["on_time_pct"]},indent=2))


if __name__ == "__main__":
    main()
