SELECT
    s.Source_Row_ID,
    s.Invoice,
    s.InvoiceDate,
    s.StockCode,
    s.Description,
    s.Quantity,
    s.Price,
    s."Customer ID",
    s.KPI_Eligibility_Status,
    ROUND(a.gross_units / 1000.0, 2)
        AS gross_merchandise_gbp,
    ROUND(a.cancellation_units / 1000.0, 2)
        AS cancellation_marked_gbp
FROM analysis_transactions AS a
JOIN source_transactions AS s
    ON s.Source_Row_ID = a.source_row_id
WHERE a.customer_key = '12346'
  AND s.StockCode = '23166'
ORDER BY s.InvoiceDate, s.Source_Row_ID;