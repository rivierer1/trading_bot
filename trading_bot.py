import time
import schedule
from datetime import datetime, time as dt_time
import pytz
from config import TradingConfig, STRATEGIES
from tos_client import ThinkOrSwimClient
from twitter_client import TwitterClient
from ai_analyzer import AIAnalyzer

class TradingBot:
    def __init__(self, config: TradingConfig):
        self.config = config
        self.tos = ThinkOrSwimClient()
        self.twitter = TwitterClient()
        self.ai = AIAnalyzer()
        self.est_tz = pytz.timezone('US/Eastern')
        self.running = False
        self.update_handler = None

    def is_market_open(self):
        now = datetime.now(self.est_tz)
        market_start = dt_time.fromisoformat(self.config.trading_hours_start)
        market_end = dt_time.fromisoformat(self.config.trading_hours_end)
        current_time = now.time()
        return market_start <= current_time <= market_end

    def set_update_handler(self, handler):
        """Set the handler for UI updates"""
        self.update_handler = handler

    def notify_update(self, update_type, data):
        """Notify the UI of updates"""
        if self.update_handler:
            self.update_handler(update_type, data)

    def analyze_symbol(self, symbol):
        # Get market data
        price_history = self.tos.get_price_history(symbol)
        if price_history is None:
            return None

        # Get relevant tweets
        tweets = self.twitter.get_tweets(
            [symbol] + self.config.twitter_keywords,
            hours_lookback=STRATEGIES['sentiment']['lookback_period']
        )

        # Analyze sentiment
        tweet_texts = [tweet['text'] for tweet in tweets]
        sentiment_score = self.ai.analyze_sentiment(tweet_texts)

        # Get market context
        market_context = self.ai.analyze_market_context(
            price_history.tail().to_string(),
            tweet_texts
        )

        # Notify UI of updates
        self.notify_update('sentiment', {
            'score': sentiment_score,
            'tweets': tweets
        })

        return {
            'symbol': symbol,
            'price_data': price_history,
            'sentiment_score': sentiment_score,
            'market_context': market_context
        }

    def execute_trade(self, symbol, action, quantity):
        try:
            response = self.tos.place_order(symbol, quantity, instruction=action)
            
            # Notify UI of the trade
            trade_data = {
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'price': float(self.tos.get_quote(symbol)[symbol]['lastPrice']),
                'time': datetime.now().isoformat()
            }
            self.notify_update('trades', [trade_data])
            
            print(f"Trade executed: {action} {quantity} shares of {symbol}")
            return response
        except Exception as e:
            print(f"Error executing trade: {e}")
            return None

    def stop(self):
        """Stop the trading bot"""
        self.running = False

    def start(self):
        """Start the trading bot"""
        print("Starting trading bot...")
        self.running = True
        
        while self.running:
            if not self.is_market_open():
                print("Market is closed. Waiting...")
                time.sleep(60)
                continue

            for symbol in self.config.symbols:
                if not self.running:
                    break
                    
                analysis = self.analyze_symbol(symbol)
                if analysis is None:
                    continue

                # Get current positions
                positions = self.tos.get_account_positions()
                self.notify_update('positions', positions)

                # Get current price and notify UI
                current_price = float(self.tos.get_quote(symbol)[symbol]['lastPrice'])
                self.notify_update('price', {'symbol': symbol, 'price': current_price})

                # Trading decision based on sentiment and technical analysis
                if analysis['sentiment_score'] > self.config.sentiment_threshold:
                    quantity = int(self.config.max_position_size / current_price)
                    self.execute_trade(symbol, 'BUY', quantity)
                elif analysis['sentiment_score'] < -self.config.sentiment_threshold:
                    quantity = int(self.config.max_position_size / current_price)
                    self.execute_trade(symbol, 'SELL', quantity)

            time.sleep(5)  # Wait 5 seconds before next iteration
