import logging
from datetime import datetime, timedelta
import pandas as pd
from tos_client import ThinkOrSwimClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self):
        self.tos_client = ThinkOrSwimClient()
        self.cache = {}
        self.cache_timeout = 60  # Cache timeout in seconds

    def _is_cache_valid(self, key):
        """Check if cached data is still valid"""
        if key not in self.cache:
            return False
        data, timestamp = self.cache[key]
        age = (datetime.now() - timestamp).total_seconds()
        return age < self.cache_timeout

    def _get_from_cache(self, key):
        """Get data from cache if valid"""
        if self._is_cache_valid(key):
            return self.cache[key][0]
        return None

    def _store_in_cache(self, key, data):
        """Store data in cache with current timestamp"""
        self.cache[key] = (data, datetime.now())

    def get_market_snapshot(self, symbols):
        """Get current market snapshot for multiple symbols"""
        cache_key = f"snapshot_{','.join(symbols)}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        quotes = self.tos_client.get_multiple_quotes(symbols)
        if quotes:
            # Process and format the data
            snapshot = {
                symbol: {
                    'price': quote.get('lastPrice'),
                    'change': quote.get('regularMarketPercentChangeInDouble'),
                    'volume': quote.get('totalVolume'),
                    'time': datetime.fromtimestamp(quote.get('quoteTimeInLong')/1000) if quote.get('quoteTimeInLong') else None
                }
                for symbol, quote in quotes.items()
            }
            self._store_in_cache(cache_key, snapshot)
            return snapshot
        return None

    def get_technical_indicators(self, symbol, days=5):
        """Calculate technical indicators for a symbol"""
        df = self.tos_client.get_price_history(symbol, period=days)
        if df is None:
            return None

        # Calculate some basic technical indicators
        df['SMA_5'] = df['close'].rolling(window=5).mean()
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['RSI'] = self._calculate_rsi(df['close'])
        
        return {
            'current_price': df['close'].iloc[-1],
            'sma_5': df['SMA_5'].iloc[-1],
            'sma_20': df['SMA_20'].iloc[-1],
            'rsi': df['RSI'].iloc[-1],
            'volume': df['volume'].iloc[-1]
        }

    def _calculate_rsi(self, prices, periods=14):
        """Calculate RSI technical indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def get_market_breadth(self):
        """Get market breadth indicators"""
        # Get S&P 500 movers
        up_movers = self.tos_client.get_movers('$SPX.X', direction='up')
        down_movers = self.tos_client.get_movers('$SPX.X', direction='down')
        
        return {
            'advancing': len(up_movers) if up_movers else 0,
            'declining': len(down_movers) if down_movers else 0,
            'top_gainers': up_movers[:5] if up_movers else [],
            'top_losers': down_movers[:5] if down_movers else []
        }

    def get_intraday_vwap(self, symbol):
        """Calculate VWAP (Volume Weighted Average Price) for today"""
        df = self.tos_client.get_intraday_data(symbol, days_back=1)
        if df is None:
            return None

        df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
        return df['vwap'].iloc[-1]

    def is_market_open(self):
        """Check if the market is currently open"""
        hours = self.tos_client.get_market_hours(['EQUITY'])
        if not hours or 'equity' not in hours:
            return False
            
        market_hours = hours['equity']['EQ']
        if not market_hours.get('isOpen'):
            return False
            
        return True
