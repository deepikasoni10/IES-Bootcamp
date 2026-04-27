/**
 * Component 2: Schema Mapper
 * Maps DISCOM internal tabular data → IES DatasetPayload JSON-LD
 * Configurable via YAML/JSON mapping configs (one per DISCOM).
 */

/**
 * Hardcoded mapping for Maharashtra DISCOM (mh_discom).
 * In production: load from YAML config per DISCOM.
 * Format: { sourceColumn: 'target.path.in.payload' }
 */
const MH_DISCOM_MAPPING = {
  // Revenue Requirement
  'Total Revenue (Rs Cr)':        'data.revenue_requirement.total_revenue_rs_crore',
  'Power Purchase Cost (Rs Cr)':  'data.revenue_requirement.power_purchase_cost_rs_crore',
  'O&M Expenses (Rs Cr)':         'data.revenue_requirement.om_expenses_rs_crore',
  'Depreciation (Rs Cr)':         'data.revenue_requirement.depreciation_rs_crore',
  'Interest on Loans (Rs Cr)':    'data.revenue_requirement.interest_on_loans_rs_crore',
  'Return on Equity (Rs Cr)':     'data.revenue_requirement.return_on_equity_rs_crore',
  // Cost of Supply
  'Cost per Unit (Rs)':           'data.cost_of_supply.cost_per_unit_rs',
  'AT&C Losses (%)':              'data.cost_of_supply.at_losses_percent',
  'Distribution Losses (%)':      'data.cost_of_supply.distribution_losses_percent',
  // Demand Forecast
  'Peak Demand (MW)':             'data.demand_forecast.peak_demand_mw',
  'Energy Requirement (MU)':      'data.demand_forecast.energy_requirement_mu',
  'Connected Load (MW)':          'data.demand_forecast.connected_load_mw',
  'Consumer Count':               'data.demand_forecast.consumer_count',
  // Capital Expenditure
  'Total CAPEX (Rs Cr)':           'data.capital_expenditure.total_capex_rs_crore',
  'Distribution Network (Rs Cr)':  'data.capital_expenditure.distribution_network_rs_crore',
  'Metering (Rs Cr)':              'data.capital_expenditure.metering_rs_crore',
  'IT Systems (Rs Cr)':            'data.capital_expenditure.it_systems_rs_crore',
};

/**
 * Set a nested value in an object by dot-notation path.
 * e.g. setPath(obj, 'data.revenue_requirement.total', 100)
 */
function setPath(obj, path, value) {
  const parts = path.split('.');
  let cur = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    if (!cur[parts[i]]) cur[parts[i]] = {};
    cur = cur[parts[i]];
  }
  cur[parts[parts.length - 1]] = value;
}

/**
 * Parse a value: try number first, then string.
 */
function parseValue(raw) {
  if (raw === null || raw === undefined || raw === '') return null;
  const num = parseFloat(String(raw).replace(/,/g, ''));
  if (!isNaN(num)) return num;
  const int = parseInt(String(raw).replace(/,/g, ''), 10);
  if (!isNaN(int)) return int;
  return raw;
}

/**
 * Map parsed tabular data → IES DatasetPayload JSON-LD
 *
 * @param {object} parsedData   - Output of fileParser.parseFile()
 * @param {string} discomId     - DISCOM participant ID
 * @param {string} financialYear - e.g. "2026-27"
 * @param {string} mappingConfig - Which mapping to use ('mh_discom' | 'custom')
 * @param {object} [customMapping] - Optional custom column → path map
 * @returns {object} DatasetPayload JSON-LD
 */
export function mapToDatasetPayload(parsedData, discomId, financialYear, mappingConfig = 'mh_discom', customMapping = null) {
  const mapping = customMapping || MH_DISCOM_MAPPING;

  // Use the first sheet (or 'Revenue Requirement' if multi-sheet)
  const sheets = parsedData.sheets;
  const firstRow = (sheets['Revenue Requirement'] || Object.values(sheets)[0])?.[0] || {};

  // Build payload skeleton
  const payload = {
    '@context': 'https://ies.energy/schemas/v1/context.jsonld',
    '@type': 'ARRPetition',
    financial_year: financialYear,
    filing_category: 'aggregate_revenue_requirement',
    discom_id: discomId,
    data: {
      revenue_requirement:  {},
      cost_of_supply:       {},
      demand_forecast:      {},
      capital_expenditure:  {},
    },
  };

  // Walk all sheets to pick up values
  for (const [, rows] of Object.entries(sheets)) {
    for (const row of rows) {
      for (const [col, targetPath] of Object.entries(mapping)) {
        if (col in row && row[col] !== null && row[col] !== '') {
          setPath(payload, targetPath, parseValue(row[col]));
        }
      }
    }
  }

  // Also check top-level row (single-sheet flat CSV)
  for (const [col, targetPath] of Object.entries(mapping)) {
    if (col in firstRow && firstRow[col] !== null && firstRow[col] !== '') {
      setPath(payload, targetPath, parseValue(firstRow[col]));
    }
  }

  return payload;
}

/**
 * Return which source columns are mapped and which are unmapped.
 */
export function getMappingStatus(columns, mappingConfig = 'mh_discom') {
  const mapping = MH_DISCOM_MAPPING;
  return columns.map(col => ({
    source: col,
    target: mapping[col] || null,
    mapped: col in mapping,
  }));
}

export { MH_DISCOM_MAPPING };
