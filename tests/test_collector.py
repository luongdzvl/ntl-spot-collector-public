import unittest
from collector import SourceError, collect, validate_ticker, push_snapshot
NOW = 1794300000000
def row(symbol="BTCUSDT", close_time=NOW):
    return {"symbol": symbol, "lastPrice": "101.5", "openPrice": "100", "highPrice": "103", "lowPrice": "99", "quoteVolume": "120000", "closeTime": close_time}
class CollectorTests(unittest.TestCase):
    def test_valid(self):
        self.assertAlmostEqual(validate_ticker(row(), "BTCUSDT", NOW)["change24hPercent"], 1.5)
    def test_mismatch(self):
        with self.assertRaises(SourceError): validate_ticker(row("ETHUSDT"), "BTCUSDT", NOW)
    def test_stale(self):
        with self.assertRaises(SourceError): validate_ticker(row(close_time=NOW-600001), "BTCUSDT", NOW)
    def test_future(self):
        with self.assertRaises(SourceError): validate_ticker(row(close_time=NOW+30001), "BTCUSDT", NOW)
    def test_nan(self):
        r=row(); r["lastPrice"]="NaN"
        with self.assertRaises(SourceError): validate_ticker(r, "BTCUSDT", NOW)
    def test_all_four(self):
        s=collect(now_ms=NOW, loader=lambda symbol: row(symbol))
        self.assertTrue(s["ok"])
        self.assertEqual(len(s["items"]), 4)
        self.assertEqual(s["coverage"]["markets"], ["spot"])
    def test_partial(self):
        def loader(symbol):
            if symbol=="BNBUSDT": raise SourceError(symbol, "HTTP_403")
            return row(symbol)
        s=collect(now_ms=NOW, loader=loader)
        self.assertFalse(s["ok"])
        self.assertEqual(s["dataStatus"], "partial")
    def test_insecure_url(self):
        with self.assertRaises(ValueError): push_snapshot({}, "http://localhost/v1/ingest", "x"*40)
    def test_short_token(self):
        with self.assertRaises(ValueError): push_snapshot({}, "https://example.com/v1/ingest", "short")
if __name__ == "__main__": unittest.main()
