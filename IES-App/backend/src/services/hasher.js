/**
 * Component 3: Content Hasher (SHA-256)
 * Computes canonical SHA-256 hash over DatasetPayload.
 * Canonical = sorted keys, no whitespace — ensures hash reproducibility.
 */
import { createHash } from 'crypto';

/**
 * Recursively sort object keys (canonical JSON-LD form)
 */
function sortKeys(obj) {
  if (Array.isArray(obj))       return obj.map(sortKeys);
  if (obj === null)             return null;
  if (typeof obj !== 'object')  return obj;
  return Object.fromEntries(
    Object.keys(obj).sort().map(k => [k, sortKeys(obj[k])])
  );
}

/**
 * Serialize to canonical JSON (sorted keys, no whitespace)
 */
export function toCanonicalJson(obj) {
  return JSON.stringify(sortKeys(obj));
}

/**
 * Compute sha256:hex over the DatasetPayload
 * @param {object} datasetPayload
 * @returns {string}  e.g. "sha256:a3f2b8c9..."
 */
export function computeHash(datasetPayload) {
  const canonical = toCanonicalJson(datasetPayload);
  const hex = createHash('sha256').update(canonical, 'utf8').digest('hex');
  return `sha256:${hex}`;
}

/**
 * Verify that a hash matches a payload
 */
export function verifyHash(datasetPayload, expectedHash) {
  return computeHash(datasetPayload) === expectedHash;
}
