WITH scenarios AS (
    SELECT
        'All eligible records' AS scenario,
        SUM(gross_units) AS gross_units,
        SUM(cancellation_units) AS cancellation_units
    FROM analysis_transactions
    WHERE month BETWEEN '2011-01' AND '2011-11'

    UNION ALL

    SELECT
        'Excluding reviewed pair (sensitivity only)',
        SUM(gross_units),
        SUM(cancellation_units)
    FROM analysis_transactions
    WHERE month BETWEEN '2011-01' AND '2011-11'
      AND source_row_id NOT IN (
          'Year 2010-2011!61621',
          'Year 2010-2011!61626'
      )
)
SELECT
    scenario,
    ROUND(gross_units / 1000.0, 2)
        AS gross_merchandise_gbp,
    ROUND(cancellation_units / 1000.0, 2)
        AS cancellation_marked_gbp,
    ROUND((gross_units - cancellation_units) / 1000.0, 2)
        AS net_merchandise_gbp,
    ROUND(
        100.0 * cancellation_units / NULLIF(gross_units, 0),
        2
    ) AS cancellation_value_ratio_pct
FROM scenarios;