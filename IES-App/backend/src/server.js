import 'dotenv/config';
import app         from './app.js';
import { config }  from './config/index.js';

const server = app.listen(config.port, () => {
  console.log('\n╔══════════════════════════════════════════════════════════╗');
  console.log('║        IES Platform Backend — Infosys RDE v1.0          ║');
  console.log('╠══════════════════════════════════════════════════════════╣');
  console.log(`║  Server    : http://localhost:${config.port}                    ║`);
  console.log(`║  Mode      : ${config.beckn.useMockOnix ? 'MOCK ONIX (sandbox simulation)  ' : 'REAL ONIX (live gateway)        '} ║`);
  console.log(`║  BAP ID    : ${config.beckn.bapId.slice(0, 38)}  ║`);
  console.log(`║  BPP ID    : ${config.beckn.bppId.slice(0, 38)}  ║`);
  console.log(`║  Callbacks : ${config.beckn.bapUri.slice(0, 38)}  ║`);
  console.log('╠══════════════════════════════════════════════════════════╣');
  console.log('║  POST /api/filings/upload    → Parse CSV/Excel          ║');
  console.log('║  POST /api/filings/map       → DatasetPayload JSON-LD   ║');
  console.log('║  POST /api/filings/hash      → SHA-256 canonical hash   ║');
  console.log('║  POST /api/filings/validate  → IES schema validation    ║');
  console.log('║  POST /api/filings/init      → Beckn /init (draft)      ║');
  console.log('║  POST /api/filings/confirm   → Beckn /confirm (formal)  ║');
  console.log('║  GET  /api/filings/:id/status→ Beckn /status            ║');
  console.log('║  POST /callback/on_init      → SERC ValidationReport    ║');
  console.log('║  POST /callback/on_confirm   → SERC signed Receipt      ║');
  console.log('╚══════════════════════════════════════════════════════════╝\n');
});

// Graceful shutdown
process.on('SIGTERM', () => { server.close(() => { console.log('Server shut down gracefully'); process.exit(0); }); });
process.on('SIGINT',  () => { server.close(() => { console.log('Server shut down gracefully'); process.exit(0); }); });
