# NTL Spot Collector (Public Staging)

Public **code only**, for a no-cost GitHub Actions-hosted Binance Spot read-only collector. Not a trading bot, not market-wide coverage, and not real-time websocket data.

## What is implemented

- Read-only Binance public Spot 24h ticker endpoint for BTCUSDT, ETHUSDT, SOLUSDT and BNBUSDT
- Four-symbol normalization, freshness validation, and 9 offline Python tests
- GitHub Actions workflow with manual trigger and an automatic **5-minute** schedule, enabled after a successful staging ingest test on 10 Nov 2026
- Secure HTTPS POST with a long shared Bearer secret to a separate Cloudflare staging Worker
- No Futures API requests, orders, wallets, Binance trading API keys, Cloudflare production writes, or secrets committed in source
- Fail-closed on incomplete or stale samples

## Configure (in THIS repo only)

Repository **Settings → Secrets and variables → Actions → New repository secret**:

1. `NTL_INGEST_URL`: HTTPS URL of your dedicated staging Cloudflare Worker ending in `/v1/ingest`
2. `NTL_INGEST_TOKEN`: the exact same random token already configured as a Secret on that Cloudflare staging Worker

Never paste these values in a GitHub file, issue, Pull Request, or chat. The token is not retrievable from Cloudflare after storing; if lost, rotate in Cloudflare and both repositories as appropriate.

## Manual smoke test

**Actions → NTL Spot Collector (Public Staging) → Run workflow**.

Expected log:
```
COLLECTOR_STATUS=fresh
ACCEPTED=4/4
ERRORS=[]
INGEST_PASS: Cloudflare accepted 4 Spot records
```

Check staging `/health` within 10 minutes of a successful run: `status: READY`, `acceptedItems: 4`.

## Future five-minute schedule

Enabled: `cron: "2-59/5 * * * *"`, i.e. UTC minute 02, 07, 12, ... 57 every hour. The earlier private repository's 30-minute schedule was removed before this change; it remains manual only. Scheduled GitHub Actions are best-effort and may be delayed or dropped. Public standard runners are included at no charge, subject to GitHub policies and service availability; Cloudflare Free quota is account-wide, and frequent calls may be restricted by Binance. The scheduling itself must be verified by observing a GitHub run with event type `schedule`.

Public repository visibility is permanent for existing content/history even if later changed; no secrets or personally sensitive data should be committed.

**Production isolation:** the existing Cloudflare `ntl-v11-cloud-sentinel` Worker and `ntl-v11-omnibrain-kv` remain untouched.

## Disable collector

GitHub → Actions → Select workflow → top right workflow menu → Disable workflow.
