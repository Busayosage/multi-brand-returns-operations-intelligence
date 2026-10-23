WITH yearly AS (
    SELECT
        SUBSTR(month, 1, 4) AS year,
        SUM(gross_units) AS gross_units,
        SUM(cancellation_units) AS cancellation_units,
        SUM(gross_units) - SUM(cancellation_units)
            AS net_units,
        COUNT(DISTINCT CASE
            WHEN sales_eligible = 1 THEN invoice_key
        END) AS sales_orders
    FROM analysis_transactions
    WHERE month BETWEEN '2010-01' AND '2010-11'
       OR month BETWEEN '2011-01' AND '2011-11'
    GROUP BY SUBSTR(month, 1, 4)
)
SELECT
    current.year,
    ROUND(current.gross_units / 1000.0, 2)
        AS gross_merchandise_gbp,
    ROUND(current.cancellation_units / 1000.0, 2)
        AS cancellation_marked_gbp,
    ROUND(current.net_units / 1000.0, 2)
        AS net_merchandise_gbp,
    current.sales_orders,
    ROUND(
        current.gross_units / 1000.0
        / NULLIF(current.sales_orders, 0), 2
    ) AS average_merchandise_order_value_gbp,
    ROUND(
        100.0 * (current.net_units - previous.net_units)
        / NULLIF(previous.net_units, 0), 2
    ) AS net_value_growth_pct,
    ROUND(
        100.0 * (current.sales_orders - previous.sales_orders)
        / NULLIF(previous.sales_orders, 0), 2
    ) AS order_growth_pct
FROM yearly AS current
LEFT JOIN yearly AS previous
    ON CAST(previous.year AS INTEGER)
       = CAST(current.year AS INTEGER) - 1
ORDER BY current.year;