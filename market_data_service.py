import logging
from datetime import datetime, timedelta
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockQuotesRequest
from alpaca.data.timeframe import TimeFrame
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.api_secret = os.getenv('ALPACA_API_SECRET')
        
        if not all([self.api_key, self.api_secret]):
            raise ValueError("Alpaca API credentials not found in environment variables")
            
        self.data_client = StockHistoricalDataClient(self.api_key, self.api_secret)
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
        try:
            cache_key = f"snapshot_{','.join(symbols)}"
            cached_data = self._get_from_cache(cache_key)
            if cached_data:
                return cached_data

            # Get latest bars for the symbols
            end = datetime.now()
            start = end - timedelta(days=1)  # Get last day of data
            
            request = StockBarsRequest(
                symbol_or_symbols=symbols,
                timeframe=TimeFrame.Hour,
                start=start,
                end=end
            )
            
            bars = self.data_client.get_stock_bars(request)
            
            if not bars:
                logger.warning("No market data received")
                return None
                
            # Process and format the data
            snapshot = {}
            for symbol in symbols:
                if symbol in bars:
                    latest_bar = bars[symbol][-1]
                    prev_bar = bars[symbol][-2] if len(bars[symbol]) > 1 else None
                    
                    change_pct = 0
                    if prev_bar:
                        change_pct = ((latest_bar.close - prev_bar.close) / prev_bar.close) * 100
                        
                    snapshot[symbol] = {
                        'price': float(latest_bar.close),
                        'change': float(change_pct),
                        'volume': int(latest_bar.volume),
                        'time': latest_bar.timestamp.isoformat()
                    }
            
            self._store_in_cache(cache_key, snapshot)
            return snapshot
            
        except Exception as e:
            logger.error(f"Error getting market snapshot: {e}", exc_info=True)
            return None

    def get_technical_indicators(self, symbol, days=5):
        """Calculate technical indicators for a symbol"""
        try:
            end = datetime.now()
            start = end - timedelta(days=days)
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start,
                end=end
            )
            
            bars = self.data_client.get_stock_bars(request)
            
            if not bars or symbol not in bars:
                logger.warning(f"No data received for {symbol}")
                return None
                
            # Convert to pandas DataFrame
            df = pd.DataFrame([{
                'close': float(bar.close),
                'volume': int(bar.volume)
            } for bar in bars[symbol]])
            
            # Calculate technical indicators
            df['SMA_5'] = df['close'].rolling(window=5).mean()
            df['SMA_20'] = df['close'].rolling(window=20).mean()
            df['RSI'] = self._calculate_rsi(df['close'])
            
            return {
                'current_price': float(df['close'].iloc[-1]),
                'sma_5': float(df['SMA_5'].iloc[-1]) if not pd.isna(df['SMA_5'].iloc[-1]) else None,
                'sma_20': float(df['SMA_20'].iloc[-1]) if not pd.isna(df['SMA_20'].iloc[-1]) else None,
                'rsi': float(df['RSI'].iloc[-1]) if not pd.isna(df['RSI'].iloc[-1]) else None,
                'volume': int(df['volume'].iloc[-1])
            }
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators for {symbol}: {e}", exc_info=True)
            return None

    def _calculate_rsi(self, prices, periods=14):
        """Calculate RSI technical indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def get_market_breadth(self):
        """Get market breadth indicators"""
        try:
            # Use SPY components as a proxy for market breadth
            spy_components = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'NVDA', 'BRK.B', 'JPM', 'JNJ', 'V']  # Example components
            
            end = datetime.now()
            start = end - timedelta(days=1)
            
            request = StockBarsRequest(
                symbol_or_symbols=spy_components,
                timeframe=TimeFrame.Hour,
                start=start,
                end=end
            )
            
            bars = self.data_client.get_stock_bars(request)
            
            if not bars:
                logger.warning("No market breadth data received")
                return None
                
            # Calculate daily changes
            changes = []
            for symbol in spy_components:
                if symbol in bars:
                    symbol_bars = bars[symbol]
                    if len(symbol_bars) >= 2:
                        first_price = float(symbol_bars[0].close)
                        last_price = float(symbol_bars[-1].close)
                        pct_change = ((last_price - first_price) / first_price) * 100
                        changes.append({'symbol': symbol, 'change': pct_change})
            
            # Sort by change
            changes.sort(key=lambda x: x['change'])
            
            advancing = len([c for c in changes if c['change'] > 0])
            declining = len([c for c in changes if c['change'] < 0])
            
            return {
                'advancing': advancing,
                'declining': declining,
                'top_gainers': changes[-5:],  # Top 5 gainers
                'top_losers': changes[:5]     # Top 5 losers
            }
            
        except Exception as e:
            logger.error(f"Error getting market breadth: {e}", exc_info=True)
            return None

    def get_intraday_vwap(self, symbol):
        """Calculate VWAP (Volume Weighted Average Price) for today"""
        try:
            end = datetime.now()
            start = end.replace(hour=9, minute=30, second=0, microsecond=0)  # Market open
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Minute,
                start=start,
                end=end
            )
            
            bars = self.data_client.get_stock_bars(request)
            
            if not bars or symbol not in bars:
                logger.warning(f"No intraday data received for {symbol}")
                return None
                
            # Calculate VWAP
            df = pd.DataFrame([{
                'close': float(bar.close),
                'volume': int(bar.volume),
                'typical_price': (float(bar.high) + float(bar.low) + float(bar.close)) / 3
            } for bar in bars[symbol]])
            
            df['volume_typical'] = df['typical_price'] * df['volume']
            vwap = df['volume_typical'].sum() / df['volume'].sum()
            
            return {
                'vwap': float(vwap),
                'last_price': float(df['close'].iloc[-1])
            }
            
        except Exception as e:
            logger.error(f"Error calculating VWAP for {symbol}: {e}", exc_info=True)
            return None

    def is_market_open(self):
        """Check if the market is currently open"""
        # This method is not implemented in the provided code
        pass
