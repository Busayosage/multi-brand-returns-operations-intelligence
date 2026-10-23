SELECT
    s.Source_Row_ID,
    s.Invoice,
    s.InvoiceDate,
    s.StockCode,
    s.Description,
    s.Quantity,
    s.Price,
    s."Customer ID",
    s.Country,
    ROUND(a.cancellation_units / 1000.0, 2)
        AS cancellation_marked_gbp
FROM analysis_transactions AS a
JOIN source_transactions AS s
    ON s.Source_Row_ID = a.source_row_id
WHERE a.month BETWEEN '2011-01' AND '2011-11'
  AND a.cancellation_eligible = 1
  AND s.StockCode = '23166'
ORDER BY a.cancellation_units DESC, s.Source_Row_ID;