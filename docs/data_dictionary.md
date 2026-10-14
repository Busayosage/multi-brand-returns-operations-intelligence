# Formal Data Dictionary — Phase 1

Multi-Brand Returns Operations Intelligence | Version 1.0 | 16 September 2026

## Scope and grain

Verified against both worksheets in the uploaded workbook. One raw row represents one recorded transaction line/observation, not one invoice, customer or physical return event. All eight original columns are preserved. This dictionary documents observed source fields and the already-agreed provenance fields; downstream clean/model fields are specified separately and have not been created.

The raw workbook is unchanged. Missingness below uses standard pandas Excel NA parsing. Source definitions come from the project MASTER RECORD; observed counts and types come from this profiling run. Future clean types are recommendations for implementing the existing design, not transformations already performed.

## `Invoice`

- **What it is:** Invoice identifier; a C prefix marks cancellation in the recorded source definition.
- **How obtained/calculated:** Direct source cell; no derived calculation or source edits.
- **Observed type:** `object`. Non-null distinct raw values: 53,628.
- **Missing values:** 0 (0.00% of combined raw lines).
- **Intended analytical type and key role:** Text identifier in the future clean layer. Repeated across invoice lines; not a unique row key.
- **Why needed:** Group lines into invoices and inspect cancellation activity.
- **Business question:** Which invoices and cancellation-marked invoices appear?
- **Quality/treatment boundary:** Preserve prefix and full value; mixed source types need later standardisation.

## `StockCode`

- **What it is:** Source stock/product code; may include non-merchandise codes.
- **How obtained/calculated:** Direct source cell; no derived calculation or source edits.
- **Observed type:** `object`. Non-null distinct raw values: 5,305.
- **Missing values:** 0 (0.00% of combined raw lines).
- **Intended analytical type and key role:** Text identifier in the future clean layer; not a line key.
- **Why needed:** Support product mapping and product-level analysis.
- **Business question:** Which source codes contribute to activity?
- **Quality/treatment boundary:** Preserve letters and digits; review code meaning and descriptions before building dim_product.

## `Description`

- **What it is:** Source description associated with the line/code.
- **How obtained/calculated:** Direct source cell; no derived calculation or source edits.
- **Observed type:** `object`. Non-null distinct raw values: 5,698.
- **Missing values:** 4,382 (0.41% of combined raw lines).
- **Intended analytical type and key role:** Nullable text in the future clean layer.
- **Why needed:** Make product activity understandable to users.
- **Business question:** What does this transaction line describe?
- **Quality/treatment boundary:** 4 numeric cells plus missing values; never silently fill from an unverified product mapping.

## `Quantity`

- **What it is:** Signed quantity for the transaction line.
- **How obtained/calculated:** Direct source cell; no derived calculation or source edits.
- **Observed type:** `int64`. Non-null distinct raw values: 1,057.
- **Missing values:** 0 (0.00% of combined raw lines).
- **Intended analytical type and key role:** Integer quantity; source sign retained.
- **Why needed:** Separate positive and negative activity and later calculate signed line value.
- **Business question:** How many units are recorded on the line?
- **Quality/treatment boundary:** Negative quantity does not by itself prove a physical return; inspect extremes.

## `InvoiceDate`

- **What it is:** Recorded invoice transaction date and time.
- **How obtained/calculated:** Direct source cell; no derived calculation or source edits.
- **Observed type:** `datetime64[ns]`. Non-null distinct raw values: 47,635.
- **Missing values:** 0 (0.00% of combined raw lines).
- **Intended analytical type and key role:** Timestamp without specified timezone.
- **Why needed:** Support period coverage, trends and calendar mapping.
- **Business question:** When was the transaction recorded?
- **Quality/treatment boundary:** Not a return-request, collection, warehouse or refund timestamp. Preserve source precision.

## `Price`

- **What it is:** Recorded unit price; GBP according to the existing project context.
- **How obtained/calculated:** Direct source cell; no derived calculation or source edits.
- **Observed type:** `float64`. Non-null distinct raw values: 2,807.
- **Missing values:** 0 (0.00% of combined raw lines).
- **Intended analytical type and key role:** Decimal monetary measure for the later model; currently read as float64.
- **Why needed:** Combine with Quantity in the established signed transaction-value formula.
- **Business question:** What unit value is recorded?
- **Quality/treatment boundary:** Review zero and negative values; tax basis is not established by these eight fields. Monetary storage/rounding decisions deferred.

## `Customer ID`

- **What it is:** Source customer identifier.
- **How obtained/calculated:** Direct source cell; no derived calculation or source edits.
- **Observed type:** `float64`. Non-null distinct raw values: 5,942.
- **Missing values:** 243,007 (22.77% of combined raw lines).
- **Intended analytical type and key role:** Nullable identifier; currently float64 due to missing values.
- **Why needed:** Enable eligible customer-level segmentation and mapping.
- **Business question:** Which recorded customer is associated with the line?
- **Quality/treatment boundary:** Do not use as a numerical measure or invent missing IDs; validate integer-like values before text formatting.

## `Country`

- **What it is:** Source customer-country label.
- **How obtained/calculated:** Direct source cell; no derived calculation or source edits.
- **Observed type:** `object`. Non-null distinct raw values: 43.
- **Missing values:** 0 (0.00% of combined raw lines).
- **Intended analytical type and key role:** Text category; not validated ISO geography.
- **Why needed:** Support geographical segmentation.
- **Business question:** Which customer location label is recorded?
- **Quality/treatment boundary:** Contains Unspecified and regional labels; no carrier, warehouse or shipment-route inference.

## Agreed provenance fields

| Field | What it is and calculation | Why needed / question answered | Status |
|---|---|---|---|
| `Source_Period` | Exact originating worksheet name, e.g. Year 2009-2010 | Which source sheet supplied the observation? | Used in issue examples; future raw ingestion metadata |
| `Source_Row_ID` | Sheet name plus original Excel row number, e.g. Year 2009-2010!2 | Where can the exact source observation be inspected? | Used in issue examples; unique within this workbook; workbook hash identifies the version |

These metadata fields are additional provenance, not replacements for Invoice. They are not added to the original workbook. A future additional workbook would also require its source-file identity to avoid collisions.

## Existing derived-field design — not yet implemented

| Field | Recorded calculation / meaning | Purpose and boundary |
|---|---|---|
| `Transaction_Value` | Quantity × Price | Signed transaction-line value; negative-price exceptions require review. |
| `Is_Cancellation` | Invoice begins with C | Identify source cancellation marking; not proof of a physical return. |
| `Transaction_Type` | Sale / Cancellation / other category after validation | Make record eligibility explicit; final exception rules remain to be agreed. |
| `Return_Value` | ABS(Quantity × Price) for eligible cancellation/return analysis where quantity is negative | Positive representation within an agreed eligible population; not applied to all negative-quantity lines automatically. |

No synthetic brand, carrier, warehouse, SLA, cost or process timestamp is present in the source. Their later dictionary entries must document generation rules and synthetic provenance. Existing fact_returns grain remains one modelled return event; its relationship to source lines must be documented before implementation.

## Dictionary validation

Both sheets have exactly these eight columns in the same order. Their actual counts are 525,461 and 541,910 data rows. Invoice, StockCode, Quantity, InvoiceDate, Price and Country have no detected nulls. All source dates parse; quantities and prices are numeric as read. Duplicate observations and mixed identifier types prevent treating any assumed invoice/product combination as a verified unique transaction-line key.

## Related evidence

`phase1_raw_data_profile.md` explains the measured exceptions and next decisions. `raw_profile.json` contains per-sheet and combined counts. `quality_issue_examples.json` contains bounded row-addressed examples. No cleaning treatment has yet been approved or applied.