import express from 'express';
import { config } from '../config/index.js';
import { store }  from '../store/filingStore.js';

const router  = express.Router();
const started = new Date();

router.get('/', (req, res) => {
  res.json({
    status:   'ok',
    service:  'IES Platform Backend — Infosys RDE',
    version:  '1.0.0',
    uptime:   `${Math.floor((Date.now() - started) / 1000)}s`,
    mode:     config.beckn.useMockOnix ? 'mock-onix' : 'real-onix',
    beckn: {
      domain:   config.beckn.domain,
      bapId:    config.beckn.bapId,
      bppId:    config.beckn.bppId,
      gateway:  config.beckn.gatewayUrl,
    },
    store: {
      filings: store.getAll().length,
    },
    timestamp: new Date().toISOString(),
  });
});

export default router;
