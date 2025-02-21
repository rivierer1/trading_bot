import unittest
from market_data_service import MarketDataService
import pandas as pd
from datetime import datetime, timedelta

class TestMarketDataService(unittest.TestCase):
    def setUp(self):
        self.service = MarketDataService()
        self.test_symbols = ['AAPL', 'MSFT', 'GOOGL']

    def test_market_snapshot(self):
        snapshot = self.service.get_market_snapshot(self.test_symbols)
        self.assertIsNotNone(snapshot)
        
        for symbol in self.test_symbols:
            self.assertIn(symbol, snapshot)
            data = snapshot[symbol]
            self.assertIsNotNone(data['price'])
            self.assertIsNotNone(data['change'])
            self.assertIsNotNone(data['volume'])

    def test_technical_indicators(self):
        indicators = self.service.get_technical_indicators('AAPL')
        self.assertIsNotNone(indicators)
        
        required_fields = ['current_price', 'sma_5', 'sma_20', 'rsi', 'volume']
        for field in required_fields:
            self.assertIn(field, indicators)
            self.assertIsNotNone(indicators[field])

    def test_market_breadth(self):
        breadth = self.service.get_market_breadth()
        self.assertIsNotNone(breadth)
        
        self.assertIn('advancing', breadth)
        self.assertIn('declining', breadth)
        self.assertIn('top_gainers', breadth)
        self.assertIn('top_losers', breadth)
        
        self.assertIsInstance(breadth['top_gainers'], list)
        self.assertIsInstance(breadth['top_losers'], list)

    def test_intraday_vwap(self):
        vwap = self.service.get_intraday_vwap('AAPL')
        self.assertIsNotNone(vwap)
        self.assertIsInstance(vwap, float)

    def test_market_status(self):
        is_open = self.service.is_market_open()
        self.assertIsInstance(is_open, bool)

    def test_caching(self):
        # Test that cache works
        symbol = 'AAPL'
        
        # First call should hit the API
        first_data = self.service.get_market_snapshot([symbol])
        self.assertIsNotNone(first_data)
        
        # Second call within cache timeout should return same data
        second_data = self.service.get_market_snapshot([symbol])
        self.assertEqual(first_data, second_data)
        
        # Verify cache key exists
        cache_key = f"snapshot_{symbol}"
        self.assertIn(cache_key, self.service.cache)

if __name__ == '__main__':
    unittest.main()
