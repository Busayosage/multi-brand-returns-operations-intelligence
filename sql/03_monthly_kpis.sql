SELECT
    month,
    ROUND(SUM(gross_units) / 1000.0, 2)
        AS gross_merchandise_gbp,
    ROUND(SUM(cancellation_units) / 1000.0, 2)
        AS cancellation_marked_gbp,
    ROUND(
        (SUM(gross_units) - SUM(cancellation_units))
        / 1000.0, 2
    ) AS net_recorded_merchandise_gbp,
    COUNT(DISTINCT CASE
        WHEN sales_eligible = 1 THEN invoice_key
    END) AS sales_orders,
    ROUND(
        SUM(gross_units) / 1000.0
        / NULLIF(COUNT(DISTINCT CASE
            WHEN sales_eligible = 1 THEN invoice_key
        END), 0),
        2
    ) AS average_merchandise_order_value_gbp,
    COUNT(DISTINCT CASE
        WHEN customer_sales_eligible = 1 THEN customer_key
    END) AS identified_purchasing_customers
FROM analysis_transactions
GROUP BY month
ORDER BY month;