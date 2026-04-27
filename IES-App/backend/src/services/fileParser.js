/**
 * Component 1: CSV / Excel Parser
 * Reads uploaded files and returns normalized tabular data.
 */
import { readFile } from 'fs/promises';
import csvParser from 'csv-parser';
const parseCsv = csvParser;
import { read as xlsxRead, utils as xlsxUtils } from 'xlsx';
import { createReadStream } from 'fs';
import { Readable } from 'stream';

/**
 * Parse a CSV file to array of row objects
 */
export async function parseCsvFile(filePath) {
  return new Promise((resolve, reject) => {
    const rows = [];
    createReadStream(filePath)
      .pipe(parseCsv({ trim: true, skipLines: 0 }))
      .on('data', row => rows.push(row))
      .on('end',  ()  => resolve(rows))
      .on('error', reject);
  });
}

/**
 * Parse an Excel (.xlsx / .xls) file.
 * Returns { sheetName: [rowObjects] } for all sheets.
 */
export async function parseExcelFile(filePath) {
  const buf = await readFile(filePath);
  const wb  = xlsxRead(buf, { type: 'buffer', cellDates: true });
  const result = {};
  for (const sheetName of wb.SheetNames) {
    const ws   = wb.Sheets[sheetName];
    const rows = xlsxUtils.sheet_to_json(ws, { defval: null, raw: false });
    result[sheetName] = rows;
  }
  return result;
}

/**
 * Auto-detect and parse any supported format.
 * Returns { format, sheets: { sheetName: [rows] }, columns: [string] }
 */
export async function parseFile(filePath, originalName) {
  const ext = originalName?.split('.').pop()?.toLowerCase();

  if (ext === 'csv') {
    const rows = await parseCsvFile(filePath);
    const columns = rows.length ? Object.keys(rows[0]) : [];
    return { format: 'csv', sheets: { 'Sheet1': rows }, columns };
  }

  if (ext === 'xlsx' || ext === 'xls') {
    const sheets  = await parseExcelFile(filePath);
    const firstSheetRows = Object.values(sheets)[0] || [];
    const columns = firstSheetRows.length ? Object.keys(firstSheetRows[0]) : [];
    return { format: ext, sheets, columns };
  }

  throw new Error(`Unsupported file format: .${ext}. Supported: .csv, .xlsx, .xls`);
}

/**
 * Get a flat preview (first N rows, all columns)
 */
export function getPreview(parsedData, maxRows = 5) {
  const firstSheet = Object.values(parsedData.sheets)[0] || [];
  return {
    columns: parsedData.columns,
    rows: firstSheet.slice(0, maxRows),
    totalRows: firstSheet.length,
    format: parsedData.format,
  };
}
