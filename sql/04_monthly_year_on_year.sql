WITH monthly AS (
    SELECT
        month,
        SUM(gross_units) - SUM(cancellation_units)
            AS net_units,
        COUNT(DISTINCT CASE
            WHEN sales_eligible = 1 THEN invoice_key
        END) AS sales_orders
    FROM analysis_transactions
    GROUP BY month
)
SELECT
    current.month AS month_2011,
    previous.month AS month_2010,
    ROUND(previous.net_units / 1000.0, 2)
        AS net_merchandise_2010_gbp,
    ROUND(current.net_units / 1000.0, 2)
        AS net_merchandise_2011_gbp,
    ROUND(
        100.0 * (current.net_units - previous.net_units)
        / NULLIF(previous.net_units, 0),
        2
    ) AS net_value_growth_pct,
    previous.sales_orders AS orders_2010,
    current.sales_orders AS orders_2011,
    ROUND(
        100.0 * (current.sales_orders - previous.sales_orders)
        / NULLIF(previous.sales_orders, 0),
        2
    ) AS order_growth_pct
FROM monthly AS current
JOIN monthly AS previous
    ON previous.month =
       '2010-' || SUBSTR(current.month, 6, 2)
WHERE current.month BETWEEN '2011-01' AND '2011-11'
ORDER BY current.month;