WITH country_comparison AS (
    SELECT
        COALESCE(NULLIF(TRIM(s.Country), ''), '[Unknown]')
            AS country,

        SUM(CASE WHEN a.month BETWEEN '2010-01' AND '2010-11'
            THEN a.gross_units - a.cancellation_units
            ELSE 0 END) AS net_2010_units,

        SUM(CASE WHEN a.month BETWEEN '2011-01' AND '2011-11'
            THEN a.gross_units - a.cancellation_units
            ELSE 0 END) AS net_2011_units,

        COUNT(DISTINCT CASE
            WHEN a.month BETWEEN '2010-01' AND '2010-11'
                 AND a.sales_eligible = 1
            THEN a.invoice_key END) AS orders_2010,

        COUNT(DISTINCT CASE
            WHEN a.month BETWEEN '2011-01' AND '2011-11'
                 AND a.sales_eligible = 1
            THEN a.invoice_key END) AS orders_2011

    FROM analysis_transactions AS a
    JOIN source_transactions AS s
        ON s.Source_Row_ID = a.source_row_id

    WHERE (
        a.month BETWEEN '2010-01' AND '2010-11'
        OR a.month BETWEEN '2011-01' AND '2011-11'
    )
      AND (a.sales_eligible = 1 OR a.cancellation_eligible = 1)

    GROUP BY COALESCE(NULLIF(TRIM(s.Country), ''), '[Unknown]')
)
SELECT
    country,
    ROUND(net_2010_units / 1000.0, 2)
        AS net_merchandise_2010_gbp,
    ROUND(net_2011_units / 1000.0, 2)
        AS net_merchandise_2011_gbp,
    ROUND((net_2011_units - net_2010_units) / 1000.0, 2)
        AS net_change_gbp,
    CASE WHEN net_2010_units > 0 THEN
        ROUND(
            100.0 * (net_2011_units - net_2010_units)
            / net_2010_units, 2
        )
    END AS net_growth_pct,
    orders_2010,
    orders_2011,
    orders_2011 - orders_2010 AS order_change
FROM country_comparison
ORDER BY ABS(net_2011_units - net_2010_units) DESC, country;