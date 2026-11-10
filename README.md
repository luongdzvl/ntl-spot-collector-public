# NTL Spot Collector (Public Staging)

Public **code only**, for a no-cost GitHub Actions-hosted Binance Spot read-only collector. Not a trading bot, not market-wide coverage, and not real-time websocket data.

## What is implemented

- Read-only Binance public Spot 24h ticker endpoint for BTCUSDT, ETHUSDT, SOLUSDT and BNBUSDT
- Four-symbol normalization, freshness validation, and 9 offline Python tests
- Manual GitHub Actions workflow; **no automatic schedule until staging secrets and end-to-end testing pass**
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

After smoke test succeeds, remove the earlier private repository's 30-minute schedule **before** adding `schedule: cron: "7,12,17,22,27,32,37,42,47,52,57,2 * * * *"` or `*/5 * * * *` to this workflow. Scheduled GitHub Actions are best-effort and may be delayed or dropped. Public standard runners are included at no charge, subject to GitHub policies and service availability; Cloudflare Free quota is account-wide, and frequent calls may be restricted by Binance.

Public repository visibility is permanent for existing content/history even if later changed; no secrets or personally sensitive data should be committed.

**Production isolation:** the existing Cloudflare `ntl-v11-cloud-sentinel` Worker and `ntl-v11-omnibrain-kv` remain untouched.

## Disable collector

GitHub → Actions → Select workflow → top right workflow menu → Disable workflow.
