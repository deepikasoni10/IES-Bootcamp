import 'express-async-errors';
import express        from 'express';
import cors           from 'cors';
import helmet         from 'helmet';
import morgan         from 'morgan';
import { config }     from './config/index.js';
import filingsRouter  from './routes/filings.js';
import callbackRouter from './routes/callback.js';
import healthRouter   from './routes/health.js';
import { errorHandler, notFound } from './middleware/errorHandler.js';

const app = express();

// ── Security & Utilities ──────────────────────────────────────────────
app.use(helmet({ contentSecurityPolicy: false }));
app.use(cors({
  origin:      config.frontendUrl,
  credentials: true,
  methods:     ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));
app.use(morgan(config.env === 'development' ? 'dev' : 'combined'));

// ── Routes ────────────────────────────────────────────────────────────
app.use('/api/health',   healthRouter);
app.use('/api/filings',  filingsRouter);
app.use('/callback',     callbackRouter);  // Beckn async callbacks

// Serve stored payloads (for payload_url reference)
import { store as payloadStore } from './store/filingStore.js';
app.get('/payloads/:txnId', (req, res) => {
  const filing = payloadStore.getByTxn(req.params.txnId);
  if (!filing?.datasetPayload) return res.status(404).json({ error: 'Payload not found' });
  res.json(filing.datasetPayload);
});

// ── Error Handling ────────────────────────────────────────────────────
app.use(notFound);
app.use(errorHandler);

export default app;
