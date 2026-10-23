WITH RECURSIVE months(month) AS (
    SELECT '2010-01'
    UNION ALL
    SELECT strftime('%Y-%m', month || '-01', '+1 month')
    FROM months
    WHERE month < '2011-11'
),
customer_monthly AS (
    SELECT
        a.month,
        SUM(a.gross_units) AS gross_units,
        SUM(a.cancellation_units) AS cancellation_units,
        COUNT(DISTINCT CASE
            WHEN a.sales_eligible = 1 THEN a.invoice_key
        END) AS sales_orders
    FROM analysis_transactions AS a
    JOIN source_transactions AS s
        ON s.Source_Row_ID = a.source_row_id
    WHERE a.customer_key = '12415'
      AND TRIM(s.Country) = 'Australia'
      AND (
          a.month BETWEEN '2010-01' AND '2010-11'
          OR a.month BETWEEN '2011-01' AND '2011-11'
      )
      AND (a.sales_eligible = 1 OR a.cancellation_eligible = 1)
    GROUP BY a.month
)
SELECT
    m.month,
    COALESCE(c.sales_orders, 0) AS sales_orders,
    ROUND(COALESCE(c.gross_units, 0) / 1000.0, 2)
        AS gross_merchandise_gbp,
    ROUND(COALESCE(c.cancellation_units, 0) / 1000.0, 2)
        AS cancellation_marked_gbp,
    ROUND(
        (COALESCE(c.gross_units, 0)
         - COALESCE(c.cancellation_units, 0)) / 1000.0,
        2
    ) AS net_merchandise_gbp
FROM months AS m
LEFT JOIN customer_monthly AS c
    ON c.month = m.month
WHERE SUBSTR(m.month, 6, 2) <> '12'
ORDER BY m.month;