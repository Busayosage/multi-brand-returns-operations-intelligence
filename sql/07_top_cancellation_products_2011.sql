WITH products AS (
    SELECT
        s.StockCode,
        MIN(TRIM(s.Description)) AS example_description,
        SUM(a.gross_units) AS gross_units,
        SUM(a.cancellation_units) AS cancellation_units,
        SUM(a.cancellation_eligible) AS cancellation_lines
    FROM analysis_transactions AS a
    JOIN source_transactions AS s
        ON s.Source_Row_ID = a.source_row_id
    WHERE a.month BETWEEN '2011-01' AND '2011-11'
      AND (
          a.sales_eligible = 1
          OR a.cancellation_eligible = 1
      )
    GROUP BY s.StockCode
)
SELECT
    StockCode,
    example_description,
    ROUND(gross_units / 1000.0, 2)
        AS gross_merchandise_gbp,
    ROUND(cancellation_units / 1000.0, 2)
        AS cancellation_marked_gbp,
    cancellation_lines,
    ROUND(
        100.0 * cancellation_units
        / NULLIF(gross_units, 0), 2
    ) AS cancellation_value_ratio_pct,
    ROUND(
        100.0 * cancellation_units
        / NULLIF(
            (SELECT SUM(cancellation_units) FROM products),
            0
        ), 2
    ) AS share_of_total_cancellation_value_pct
FROM products
WHERE cancellation_units > 0
ORDER BY cancellation_units DESC, StockCode
LIMIT 10;