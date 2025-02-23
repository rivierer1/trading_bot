import time
import schedule
from datetime import datetime, time as dt_time
import pytz
from config import TradingConfig, STRATEGIES
from alpaca_client import AlpacaClient
from ai_analyzer import AIAnalyzer
from market_data_service import MarketDataService

class TradingBot:
    def __init__(self, config: TradingConfig):
        self.config = config
        self.alpaca = AlpacaClient()
        self.market_data = MarketDataService()
        self.ai = AIAnalyzer()
        self.est_tz = pytz.timezone('US/Eastern')
        self.running = False
        self.update_handler = None

    def is_market_open(self):
        try:
            clock = self.alpaca.get_clock()
            return clock['is_open'] if clock else False
        except Exception as e:
            print(f"Error checking market status: {e}")
            return False

    def set_update_handler(self, handler):
        """Set the handler for UI updates"""
        self.update_handler = handler

    def notify_update(self, update_type, data):
        """Notify the UI of updates"""
        if self.update_handler:
            self.update_handler(update_type, data)

    def analyze_symbol(self, symbol):
        try:
            # Get market data
            snapshot = self.market_data.get_market_snapshot([symbol])
            if not snapshot or symbol not in snapshot:
                print(f"No market data available for {symbol}")
                return None

            # Get technical indicators
            indicators = self.market_data.get_technical_indicators(symbol)
            if not indicators:
                print(f"No technical indicators available for {symbol}")
                return None

            # Get market context
            market_context = self.ai.analyze_market_context(
                str(snapshot[symbol]),
                []  # No tweets needed since we're using technical analysis
            )

            # Notify UI of updates
            self.notify_update('market_data', {
                'symbol': symbol,
                'snapshot': snapshot[symbol],
                'indicators': indicators
            })

            return {
                'symbol': symbol,
                'snapshot': snapshot[symbol],
                'indicators': indicators,
                'market_context': market_context
            }
        except Exception as e:
            print(f"Error analyzing symbol {symbol}: {e}")
            return None

    def execute_trade(self, symbol, action, quantity):
        try:
            # Convert action to Alpaca's side format
            side = 'buy' if action.upper() == 'BUY' else 'sell'
            
            # Place the order
            order = self.alpaca.submit_order(
                symbol=symbol,
                qty=quantity,
                side=side,
                type='market',
                time_in_force='day'
            )
            
            if order:
                # Get the current quote
                snapshot = self.market_data.get_market_snapshot([symbol])
                price = snapshot[symbol]['price'] if snapshot and symbol in snapshot else None
                
                # Notify UI of the trade
                trade_data = {
                    'symbol': symbol,
                    'action': action,
                    'quantity': quantity,
                    'price': price,
                    'time': datetime.now().isoformat(),
                    'order_id': order.get('id')
                }
                self.notify_update('trades', [trade_data])
                
                print(f"Trade executed: {action} {quantity} shares of {symbol}")
                return order
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

            try:
                for symbol in self.config.symbols:
                    if not self.running:
                        break
                        
                    analysis = self.analyze_symbol(symbol)
                    if analysis is None:
                        continue

                    # Get current positions
                    positions = self.alpaca.get_positions()
                    self.notify_update('positions', positions)

                    # Get current price
                    snapshot = self.market_data.get_market_snapshot([symbol])
                    if snapshot and symbol in snapshot:
                        current_price = snapshot[symbol]['price']
                        self.notify_update('price', {'symbol': symbol, 'price': current_price})

                        # Trading decision based on technical analysis
                        indicators = analysis['indicators']
                        if indicators:
                            # Example strategy using RSI
                            rsi = indicators.get('RSI', 50)  # Default to neutral if not available
                            
                            if rsi < 30:  # Oversold
                                quantity = int(self.config.max_position_size / current_price)
                                self.execute_trade(symbol, 'BUY', quantity)
                            elif rsi > 70:  # Overbought
                                quantity = int(self.config.max_position_size / current_price)
                                self.execute_trade(symbol, 'SELL', quantity)

                # Update portfolio
                portfolio = self.alpaca.get_portfolio_summary()
                if portfolio:
                    self.notify_update('portfolio', portfolio)

            except Exception as e:
                print(f"Error in trading loop: {e}")

            time.sleep(5)  # Wait 5 seconds before next iteration
