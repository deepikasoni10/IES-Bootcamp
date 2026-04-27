/**
 * Component 9: Receipt Processor
 * Verifies signed SERC Receipt from on_confirm and stores with provenance.
 */
import { verifyReceiptProof } from './credentialService.js';
import { validateReceiptObj }  from './validator.js';

/**
 * Process and verify a SERC receipt.
 * 1. Validate receipt structure against IES schema
 * 2. Verify SERC signature
 * 3. Check accepted_payload_hash matches submitted hash
 *
 * @returns {{ valid: boolean, receipt: object, issues: string[] }}
 */
export function processReceipt(receipt, submittedPayloadHash) {
  const issues = [];

  // Step 1: Schema validation
  const { valid: schemaValid, errors } = validateReceiptObj(receipt);
  if (!schemaValid) {
    errors.forEach(e => issues.push(`Schema: ${e.instancePath} ${e.message}`));
  }

  // Step 2: Signature verification
  const proofResult = verifyReceiptProof(receipt);
  if (!proofResult.valid) {
    issues.push(`Proof: ${proofResult.reason}`);
  }

  // Step 3: Hash integrity check
  if (submittedPayloadHash && receipt.accepted_payload_hash !== submittedPayloadHash) {
    issues.push(`Hash mismatch: submitted="${submittedPayloadHash}" vs accepted="${receipt.accepted_payload_hash}"`);
  }

  const valid = issues.length === 0;

  return {
    valid,
    receipt,
    proofVerified:  proofResult.valid,
    hashMatches:    !submittedPayloadHash || receipt.accepted_payload_hash === submittedPayloadHash,
    schemaValid,
    issues,
    processedAt: new Date().toISOString(),
  };
}
