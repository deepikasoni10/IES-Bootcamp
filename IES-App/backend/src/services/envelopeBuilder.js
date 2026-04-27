/**
 * Component 4 & 5: CommonEnvelope Builder + Beckn Message Builder
 * Wraps DatasetPayload in IES CommonEnvelope.
 */
import { config } from '../config/index.js';

/**
 * Build the IES CommonEnvelope for a filing
 */
export function buildEnvelope({ datasetPayload, contentHash, issuerId, priorMessageId = null, priorValidatedAt = null }) {
  const envelope = {
    schema_version: 'ies:CommonEnvelope:v1.0',
    content_type:   'Filing',
    content_hash:   contentHash,
    issuer_id:      issuerId || config.credential.discomId,
    created_at:     new Date().toISOString(),
    provenance:     {},
    content:        datasetPayload,
  };

  if (priorMessageId) {
    envelope.provenance = {
      prior_message_id:   priorMessageId,
      prior_validated_at: priorValidatedAt || new Date().toISOString(),
    };
  }

  return envelope;
}

/**
 * Build the Filing object for an /init (draft) request
 */
export function buildDraftFiling({ datasetPayload, payloadHash, payloadUrl, discomId, txnId }) {
  return {
    type: 'draft_validation',
    filer: {
      id:         discomId || config.credential.discomId,
      descriptor: { name: 'Maharashtra State Electricity Distribution Co. Ltd.' },
    },
    payload_hash: payloadHash,
    payload_url:  payloadUrl || `${config.beckn.bapUri}/payloads/${txnId}`,
    dataset_payload: datasetPayload,
    envelope: buildEnvelope({ datasetPayload, contentHash: payloadHash, issuerId: discomId }),
  };
}

/**
 * Build the Filing object for a /confirm (formal) request
 */
export function buildFormalFiling({ datasetPayload, payloadHash, payloadUrl, discomId, credential, signature, txnId, draftMsgId, draftValidatedAt }) {
  return {
    type: 'formal_submission',
    filer: {
      id:         discomId || config.credential.discomId,
      descriptor: { name: 'Maharashtra State Electricity Distribution Co. Ltd.' },
      credential,
    },
    payload_hash:     payloadHash,
    payload_url:      payloadUrl || `${config.beckn.bapUri}/payloads/${txnId}`,
    dataset_payload:  datasetPayload,
    digital_signature: signature,
    envelope: buildEnvelope({
      datasetPayload,
      contentHash:     payloadHash,
      issuerId:        discomId,
      priorMessageId:  draftMsgId,
      priorValidatedAt: draftValidatedAt,
    }),
  };
}
