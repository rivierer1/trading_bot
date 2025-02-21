from dataclasses import dataclass
from typing import List, Dict

@dataclass
class TradingConfig:
    # Trading parameters
    symbols: List[str] = None
    max_position_size: float = 1000.0  # Maximum position size in dollars
    stop_loss_percentage: float = 0.02  # 2% stop loss
    take_profit_percentage: float = 0.04  # 4% take profit
    
    # Time parameters
    trading_hours_start: str = "09:30"  # Market open (EST)
    trading_hours_end: str = "16:00"    # Market close (EST)
    
    # Twitter parameters
    twitter_keywords: List[str] = None
    sentiment_threshold: float = 0.7     # Minimum sentiment score to trigger trade
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["SPY", "AAPL", "MSFT"]  # Default symbols to trade
        if self.twitter_keywords is None:
            self.twitter_keywords = ["market", "stock", "trading", "economy"]

# Trading strategies configuration
STRATEGIES = {
    "momentum": {
        "timeframe": "5m",
        "rsi_period": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30
    },
    "sentiment": {
        "lookback_period": "1h",
        "min_mentions": 5
    }
}
