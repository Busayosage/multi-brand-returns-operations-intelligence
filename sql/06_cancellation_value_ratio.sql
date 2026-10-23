SELECT
    SUBSTR(month, 1, 4) AS year,
    ROUND(SUM(gross_units) / 1000.0, 2)
        AS gross_merchandise_gbp,
    ROUND(SUM(cancellation_units) / 1000.0, 2)
        AS cancellation_marked_gbp,
    ROUND(
        100.0 * SUM(cancellation_units)
        / NULLIF(SUM(gross_units), 0),
        2
    ) AS cancellation_value_ratio_pct
FROM analysis_transactions
WHERE month BETWEEN '2010-01' AND '2010-11'
   OR month BETWEEN '2011-01' AND '2011-11'
GROUP BY SUBSTR(month, 1, 4)
ORDER BY year;