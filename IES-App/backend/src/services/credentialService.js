/**
 * Component 6: Credential Manager
 * Manages W3C Verifiable Credentials for DISCOM identity.
 * In sandbox: uses mock credentials.
 * In production: integrates with IES credential service endpoint.
 */
import { createHmac, randomUUID } from 'crypto';
import { config } from '../config/index.js';

/** Mock VC — replace with real credential service call in production */
function buildMockVC(discomId) {
  return {
    '@context': [
      'https://www.w3.org/2018/credentials/v1',
      'https://ies.energy/credentials/v1',
    ],
    type:         ['VerifiableCredential', 'EnergyParticipantCredential'],
    issuer:       'did:ies:credential-service',
    issuanceDate: '2026-04-10T00:00:00Z',
    expirationDate: '2027-04-10T00:00:00Z',
    credentialSubject: {
      id:           `did:ies:${discomId}`,
      role:         'distribution_company',
      jurisdiction: 'maharashtra',
      license_number: 'MERC/DISCOM/001',
    },
    proof: {
      type:               'Ed25519Signature2020',
      created:            new Date().toISOString(),
      verificationMethod: 'did:ies:credential-service#key-1',
      proofPurpose:       'assertionMethod',
      proofValue:         `z${randomUUID().replace(/-/g, '')}`,
    },
  };
}

/**
 * Fetch (or generate mock) Verifiable Credential for a DISCOM.
 * @returns {object} W3C Verifiable Credential
 */
export async function getVerifiableCredential(discomId = config.credential.discomId) {
  if (config.beckn.useMockOnix) {
    return buildMockVC(discomId);
  }

  // Real credential service integration
  const { default: axios } = await import('axios');
  try {
    const res = await axios.post(`${config.credential.serviceUrl}/credentials/issue`, {
      discom_id: discomId,
      type:      'EnergyParticipantCredential',
    }, { timeout: 10_000 });
    return res.data.credential;
  } catch (err) {
    console.warn('[CredentialService] Falling back to mock VC:', err.message);
    return buildMockVC(discomId);
  }
}

/**
 * Sign a payload hash with the DISCOM private key.
 * In sandbox: HMAC-based mock signature.
 * In production: Ed25519 signing with HSM/key store.
 *
 * @param {string} payloadHash  - e.g. "sha256:abc123..."
 * @param {string} discomDid    - signer DID
 * @returns {object} digital_signature object
 */
export function signPayload(payloadHash, discomDid = config.credential.discomDid) {
  // Mock signing — in production: use Ed25519 private key
  const mockKey    = 'ies-sandbox-mock-private-key-2026';
  const sigValue   = createHmac('sha256', mockKey).update(payloadHash).digest('hex');

  return {
    algorithm:       'Ed25519',
    signer_id:       discomDid,
    signature_value: `base64:${Buffer.from(sigValue).toString('base64')}`,
    signed_hash:     payloadHash,
    signed_at:       new Date().toISOString(),
  };
}

/**
 * Verify a SERC Ed25519 proof on a receipt.
 * Mock mode: always returns true.
 * Production: verify against SERC's DID/public key from registry.
 */
export function verifyReceiptProof(receipt) {
  if (config.beckn.useMockOnix) {
    // Trust mock SERC in sandbox
    return { valid: true, reason: 'Mock SERC — signature trusted in sandbox' };
  }
  // TODO: real Ed25519 verification against SERC's public key from DeDi registry
  return { valid: false, reason: 'Real verification not implemented yet' };
}
