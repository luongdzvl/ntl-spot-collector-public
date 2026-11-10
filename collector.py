"""NTL Markets V11: read-only Binance Spot market-data collector.
No trading, account access, Futures requests or secrets in output.
"""
from __future__ import annotations
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT")
BASE_URL = "https://data-api.binance.vision/api/v3/ticker/24hr"
MAX_SOURCE_AGE_MS = 10 * 60 * 1000
MAX_FUTURE_SKEW_MS = 30 * 1000
MAX_RESPONSE_BYTES = 64_000
SCHEMA = "ntl.spot.snapshot.v1"

class SourceError(Exception):
    def __init__(self, symbol: str, reason: str):
        super().__init__(f"{symbol}: {reason}")
        self.symbol = symbol
        self.reason = reason

def iso_ms(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def validate_ticker(row: Any, symbol: str, now_ms: int) -> dict[str, Any]:
    if not isinstance(row, dict) or row.get("symbol") != symbol:
        raise SourceError(symbol, "SYMBOL_MISMATCH")
    try:
        price = float(row["lastPrice"])
        opened = float(row["openPrice"])
        high = float(row["highPrice"])
        low = float(row["lowPrice"])
        volume = float(row["quoteVolume"])
        close_time = int(row["closeTime"])
    except (KeyError, ValueError, TypeError, OverflowError):
        raise SourceError(symbol, "INVALID_FIELDS") from None
    if not all(math.isfinite(v) for v in (price, opened, high, low, volume)):
        raise SourceError(symbol, "NON_FINITE")
    if (price <= 0 or opened <= 0 or low <= 0 or volume < 0
        or high < max(opened, price, low) or low > min(opened, price)
        or close_time < now_ms - MAX_SOURCE_AGE_MS
        or close_time > now_ms + MAX_FUTURE_SKEW_MS):
        raise SourceError(symbol, "INVALID_OR_STALE_SOURCE")
    change = (price / opened - 1) * 100
    if not math.isfinite(change) or abs(change) > 10_000:
        raise SourceError(symbol, "INVALID_CHANGE")
    return {
        "exchange": "BINANCE", "market": "spot", "symbol": symbol,
        "lastPrice": price, "change24hPercent": change,
        "quoteVolume": volume, "sourceEventTime": iso_ms(close_time),
        "verifiedForTrading": False, "tradeSignal": False,
    }

def get_ticker(symbol: str, *, timeout: float = 10) -> Any:
    url = BASE_URL + "?" + urllib.parse.urlencode({"symbol": symbol})
    request = urllib.request.Request(url, headers={
        "Accept": "application/json", "User-Agent": "NTL-Markets-V11-Spot-Research/1.0",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise SourceError(symbol, "HTTP_" + str(response.status))
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            if len(payload) > MAX_RESPONSE_BYTES:
                raise SourceError(symbol, "RESPONSE_TOO_LARGE")
            try:
                return json.loads(payload)
            except (UnicodeError, json.JSONDecodeError):
                raise SourceError(symbol, "INVALID_JSON") from None
    except urllib.error.HTTPError as exc:
        raise SourceError(symbol, "HTTP_" + str(exc.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SourceError(symbol, "NETWORK_" + type(exc).__name__) from None

def collect(now_ms: int | None = None, loader=get_ticker) -> dict[str, Any]:
    started_ms = int(time.time() * 1000) if now_ms is None else now_ms
    items = []
    errors = []
    for symbol in SYMBOLS:
        try:
            now = int(time.time() * 1000) if now_ms is None else now_ms
            items.append(validate_ticker(loader(symbol), symbol, now))
        except SourceError as exc:
            errors.append({"symbol": exc.symbol, "code": exc.reason})
        except Exception as exc:
            errors.append({"symbol": symbol, "code": "UNEXPECTED_" + type(exc).__name__})
    return {
        "ok": len(items) == len(SYMBOLS),
        "schemaVersion": SCHEMA, "mode": "READ_ONLY_RESEARCH",
        "source": "BINANCE_SPOT_PUBLIC", "collectedAt": iso_ms(started_ms),
        "dataStatus": "fresh" if len(items) == len(SYMBOLS) else "partial" if items else "unavailable",
        "coverage": {
            "markets": ["spot"], "symbols": list(SYMBOLS),
            "fullMarket": False, "websocketContinuous": False,
        },
        "tradeableVerified": False, "winProbability": None,
        "items": items, "errors": errors,
    }

def push_snapshot(snapshot: dict[str, Any], url: str, token: str) -> None:
    if not url.startswith("https://") or len(token) < 32 or len(token) > 512:
        raise ValueError("INVALID_INGEST_CONFIGURATION")
    parsed = urllib.parse.urlparse(url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path != "/v1/ingest":
        raise ValueError("INVALID_INGEST_URL")
    payload = json.dumps(snapshot, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST", headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "NTL-Markets-V11-Spot-Research/1.0",
    })
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            if response.status != 201:
                raise RuntimeError("INGEST_HTTP_" + str(response.status))
    except urllib.error.HTTPError as exc:
        raise RuntimeError("INGEST_HTTP_" + str(exc.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("INGEST_NETWORK_" + type(exc).__name__) from None

def main() -> int:
    snapshot = collect()
    print("COLLECTOR_STATUS=" + snapshot["dataStatus"])
    print("ACCEPTED=" + str(len(snapshot["items"])) + "/4")
    print("ERRORS=" + json.dumps(snapshot["errors"], separators=(",", ":")))
    with open("spot-snapshot.json", "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)
    if not snapshot["ok"]:
        print("NO_INGEST: incomplete or stale data")
        return 1
    url = os.getenv("NTL_INGEST_URL", "").strip()
    token = os.getenv("NTL_INGEST_TOKEN", "").strip()
    if bool(url) != bool(token):
        print("ERROR: only one ingest secret configured")
        return 1
    if not url:
        print("DRY_RUN_PASS: Spot ready; ingestion not configured")
        return 0
    try:
        push_snapshot(snapshot, url, token)
    except (ValueError, RuntimeError) as exc:
        print("INGEST_FAILED=" + str(exc))
        return 1
    print("INGEST_PASS: Cloudflare accepted 4 Spot records")
    return 0

if __name__ == "__main__":
    sys.exit(main())
