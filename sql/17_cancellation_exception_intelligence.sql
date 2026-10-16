-- Part 2: observed cancellation-marked transaction diagnostics.
-- Public UCI Online Retail II, recovered retail_analytics.db. READ-ONLY SELECTs.
-- Monetary columns store integer thousandths of GBP: divide by 1000.
-- C-prefix cancellation != confirmed physical return; do not delete the reviewed pair.
-- Periods are January-November 2010 and January-November 2011.

-- 1. Comparing cancellation counts and value with the same months in each year.
SELECT SUBSTR(month,1,4) AS year,
       SUM(cancellation_eligible) AS eligible_cancellation_lines,
       ROUND(SUM(cancellation_units)/1000.0,2) AS cancellation_marked_gbp,
       ROUND(SUM(gross_units)/1000.0,2) AS gross_merchandise_gbp,
       ROUND(100.0*SUM(cancellation_units)/NULLIF(SUM(gross_units),0),2)
         AS cancellation_value_ratio_pct
FROM analysis_transactions
WHERE month BETWEEN '2010-01' AND '2010-11'
   OR month BETWEEN '2011-01' AND '2011-11'
GROUP BY SUBSTR(month,1,4)
ORDER BY year;

-- 2. Identify and verify the source-row provenance for the reversal-like pair.
SELECT a.source_row_id, s.Invoice, s.StockCode, s.Quantity, s.Price,
       s.InvoiceDate, a.gross_units/1000.0 AS positive_sale_gbp,
       a.cancellation_units/1000.0 AS cancellation_marked_gbp
FROM analysis_transactions a
JOIN source_transactions s ON s.Source_Row_ID=a.source_row_id
WHERE a.source_row_id IN ('Year 2010-2011!61621', 'Year 2010-2011!61626')
ORDER BY s.InvoiceDate;

-- 3. Which products contribute most to posted cancellation value?
SELECT s.StockCode, MIN(TRIM(s.Description)) AS example_description,
       SUM(a.cancellation_eligible) AS cancellation_lines,
       ROUND(SUM(a.cancellation_units)/1000.0,2) AS cancellation_marked_gbp
FROM analysis_transactions a
JOIN source_transactions s ON s.Source_Row_ID=a.source_row_id
WHERE a.month BETWEEN '2011-01' AND '2011-11'
  AND (a.sales_eligible=1 OR a.cancellation_eligible=1)
GROUP BY s.StockCode
HAVING SUM(a.cancellation_units)>0
ORDER BY SUM(a.cancellation_units) DESC
LIMIT 10;

-- 4. Sensitivity, NOT a cleaned / corrected cancellation KPI.
WITH scenario AS (
 SELECT 'All eligible records (headline)' AS scenario,
        SUM(gross_units) AS gross_units,
        SUM(cancellation_units) AS cancelled_units
 FROM analysis_transactions
 WHERE month BETWEEN '2011-01' AND '2011-11'
 UNION ALL
 SELECT 'Excluding BOTH reviewed rows (sensitivity only)',
        SUM(gross_units), SUM(cancellation_units)
 FROM analysis_transactions
 WHERE month BETWEEN '2011-01' AND '2011-11'
   AND source_row_id NOT IN ('Year 2010-2011!61621','Year 2010-2011!61626')
)
SELECT scenario,
       ROUND(gross_units/1000.0,2) AS gross_merchandise_gbp,
       ROUND(cancelled_units/1000.0,2) AS cancellation_marked_gbp,
       ROUND((gross_units-cancelled_units)/1000.0,2) AS net_merchandise_gbp,
       ROUND(100.0*cancelled_units/NULLIF(gross_units,0),2) AS cancellation_value_ratio_pct
FROM scenario;
