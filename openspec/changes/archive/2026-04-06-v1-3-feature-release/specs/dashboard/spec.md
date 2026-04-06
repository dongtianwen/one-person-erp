## ADDED Requirements

### Requirement: Cashflow forecast line chart on dashboard
The dashboard SHALL display a line chart with three lines: predicted income (blue), predicted expense (red), and net value (green). X-axis shows week numbers, Y-axis shows amounts in yuan. When no data exists, the chart SHALL render a zero-value curve without errors. When the API request fails, the chart area SHALL display "数据加载失败，请刷新" without affecting other dashboard components.

#### Scenario: Chart renders with forecast data
- **WHEN** dashboard loads and cashflow forecast API returns data
- **THEN** three colored lines are displayed with correct weekly data points

#### Scenario: Chart renders zeros when no data
- **WHEN** no contracts or expense history exist
- **THEN** chart renders a zero curve, no white screen, no infinite loading

#### Scenario: Chart shows error on API failure
- **WHEN** cashflow forecast API request fails
- **THEN** chart area shows "数据加载失败，请刷新", other dashboard components unaffected

### Requirement: Quarterly VAT summary card on dashboard
The dashboard SHALL display a card showing current quarter's output_tax_total, input_tax_total, and tax_payable from the tax-summary API. When no data exists, values SHALL show 0.00. The card SHALL include a footnote: "仅供参考，不替代正式申报口径".

#### Scenario: Card shows current quarter data
- **WHEN** dashboard loads during Q2 2026
- **THEN** card displays output_tax_total, input_tax_total, tax_payable for Q2 2026

#### Scenario: Card shows zeros when no data
- **WHEN** current quarter has no invoice records
- **THEN** all three values display 0.00, no white screen

### Requirement: Invoice ledger tab on finance list page
The finance list page SHALL have an "发票台账" Tab that displays only records with non-empty invoice_no. The tab SHALL support filtering by year and quarter. Display columns: invoice_no, invoice_direction, invoice_type, amount, tax_rate, tax_amount, date.

#### Scenario: Tab shows only invoiced records
- **WHEN** user clicks "发票台账" tab
- **THEN** only records with invoice_no non-empty are displayed

#### Scenario: Filter by year and quarter
- **WHEN** user selects year=2026 and quarter=1
- **THEN** only records from Q1 2026 are shown
