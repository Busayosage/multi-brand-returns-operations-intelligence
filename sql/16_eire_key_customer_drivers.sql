SELECT
    a.customer_key AS customer,
    SUBSTR(a.month, 1, 4) AS year,
    COUNT(DISTINCT CASE
        WHEN a.sales_eligible = 1 THEN a.invoice_key
    END) AS sales_orders,
    ROUND(SUM(a.gross_units) / 1000.0, 2)
        AS gross_merchandise_gbp,
    ROUND(SUM(a.cancellation_units) / 1000.0, 2)
        AS cancellation_marked_gbp,
    ROUND(
        (SUM(a.gross_units) - SUM(a.cancellation_units))
        / 1000.0, 2
    ) AS net_merchandise_gbp,
    ROUND(
        SUM(a.gross_units) / 1000.0
        / NULLIF(COUNT(DISTINCT CASE
            WHEN a.sales_eligible = 1 THEN a.invoice_key
        END), 0),
        2
    ) AS average_merchandise_order_value_gbp
FROM analysis_transactions AS a
JOIN source_transactions AS s
    ON s.Source_Row_ID = a.source_row_id
WHERE TRIM(s.Country) = 'EIRE'
  AND a.customer_key IN ('14156', '14911')
  AND (
      a.month BETWEEN '2010-01' AND '2010-11'
      OR a.month BETWEEN '2011-01' AND '2011-11'
  )
  AND (a.sales_eligible = 1 OR a.cancellation_eligible = 1)
GROUP BY a.customer_key, SUBSTR(a.month, 1, 4)
ORDER BY customer, year;