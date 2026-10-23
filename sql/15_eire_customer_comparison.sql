WITH customer_totals AS (
    SELECT
        COALESCE(NULLIF(a.customer_key, ''), '[Unknown]')
            AS customer,
        SUM(CASE
            WHEN a.month BETWEEN '2010-01' AND '2010-11'
            THEN a.gross_units - a.cancellation_units
            ELSE 0
        END) AS net_2010_units,
        SUM(CASE
            WHEN a.month BETWEEN '2011-01' AND '2011-11'
            THEN a.gross_units - a.cancellation_units
            ELSE 0
        END) AS net_2011_units,
        COUNT(DISTINCT CASE
            WHEN a.month BETWEEN '2010-01' AND '2010-11'
                 AND a.sales_eligible = 1
            THEN a.invoice_key
        END) AS orders_2010,
        COUNT(DISTINCT CASE
            WHEN a.month BETWEEN '2011-01' AND '2011-11'
                 AND a.sales_eligible = 1
            THEN a.invoice_key
        END) AS orders_2011
    FROM analysis_transactions AS a
    JOIN source_transactions AS s
        ON s.Source_Row_ID = a.source_row_id
    WHERE TRIM(s.Country) = 'EIRE'
      AND (
          a.month BETWEEN '2010-01' AND '2010-11'
          OR a.month BETWEEN '2011-01' AND '2011-11'
      )
      AND (a.sales_eligible = 1 OR a.cancellation_eligible = 1)
    GROUP BY COALESCE(NULLIF(a.customer_key, ''), '[Unknown]')
)
SELECT
    customer,
    ROUND(net_2010_units / 1000.0, 2)
        AS net_2010_gbp,
    ROUND(net_2011_units / 1000.0, 2)
        AS net_2011_gbp,
    ROUND((net_2011_units - net_2010_units) / 1000.0, 2)
        AS net_change_gbp,
    orders_2010,
    orders_2011,
    ROUND(
        100.0 * net_2011_units
        / NULLIF(
            (SELECT SUM(net_2011_units) FROM customer_totals),
            0
        ),
        2
    ) AS share_of_eire_2011_net_pct
FROM customer_totals
ORDER BY net_change_gbp ASC, customer;