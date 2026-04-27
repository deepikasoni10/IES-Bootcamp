import 'dotenv/config';

export const config = {
  port: parseInt(process.env.PORT) || 4000,
  env: process.env.NODE_ENV || 'development',
  frontendUrl: process.env.FRONTEND_URL || 'http://localhost:5173',

  beckn: {
    useMockOnix: process.env.USE_MOCK_ONIX !== 'false',   // default true
    gatewayUrl:  process.env.ONIX_GATEWAY_URL  || 'https://gateway.sandbox.ies',
    bapId:       process.env.BAP_ID            || 'infosys-discom-bap.sandbox.ies',
    bapUri:      process.env.BAP_URI           || 'http://localhost:4000/callback',
    bppId:       process.env.BPP_ID            || 'mock-serc.sandbox.ies',
    bppUri:      process.env.BPP_URI           || 'https://mock-serc.sandbox.ies',
    domain:      process.env.BECKN_DOMAIN      || 'ies:regulatory',
    version:     process.env.BECKN_VERSION     || '1.0.0',
  },

  credential: {
    serviceUrl: process.env.CREDENTIAL_SERVICE_URL || 'https://credentials.sandbox.ies',
    discomId:   process.env.DISCOM_ID              || 'discom-maharashtra-001',
    discomDid:  process.env.DISCOM_DID             || 'did:ies:discom-maharashtra-001',
  },

  dedi: {
    url: process.env.DEDI_URL || 'https://dedi.ies.energy',
  },

  mock: {
    draftDelayMs:  parseInt(process.env.MOCK_DRAFT_DELAY_MS)  || 2500,
    formalDelayMs: parseInt(process.env.MOCK_FORMAL_DELAY_MS) || 3000,
  },
};
