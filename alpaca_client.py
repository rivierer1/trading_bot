import os
import logging
from datetime import datetime, timedelta
import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv
import time

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AlpacaClient:
    def __init__(self):
        """Initialize Alpaca client with API credentials"""
        logger.info("Initializing AlpacaClient...")
        load_dotenv()
        
        # Get API credentials
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.api_secret = os.getenv('ALPACA_API_SECRET')
        self.paper_trading = os.getenv('ALPACA_PAPER_TRADING', 'True').lower() == 'true'
        
        if not all([self.api_key, self.api_secret]):
            logger.error("Alpaca API credentials not found in environment variables")
            raise ValueError("Missing Alpaca API credentials")
            
        # Initialize clients
        logger.debug("Creating Alpaca trading client...")
        self.trading_client = TradingClient(self.api_key, self.api_secret, paper=self.paper_trading)
        
        logger.debug("Creating Alpaca data client...")
        self.data_client = StockHistoricalDataClient(self.api_key, self.api_secret)
        
        logger.info(f"Initialized Alpaca client (Paper Trading: {self.paper_trading})")
        
        # Test connection
        self.test_connection()

    def test_connection(self):
        """Test connection to Alpaca API"""
        try:
            # Get account information
            account = self.trading_client.get_account()
            logger.info("Successfully connected to Alpaca API")
            logger.info(f"Account ID: {account.id}")
            logger.info(f"Cash: ${float(account.cash):.2f}")
            logger.info(f"Portfolio Value: ${float(account.portfolio_value):.2f}")
            logger.info(f"Buying Power: ${float(account.buying_power):.2f}")
            logger.info(f"Status: {account.status}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca API: {e}")
            return False

    def get_positions(self):
        """Get current positions"""
        logger.debug("Fetching positions...")
        try:
            positions = self.trading_client.get_all_positions()
            logger.debug(f"Retrieved {len(positions)} positions")
            
            formatted_positions = [{
                'symbol': pos.symbol,
                'qty': float(pos.qty),
                'avg_entry_price': float(pos.avg_entry_price),
                'current_price': float(pos.current_price),
                'market_value': float(pos.market_value),
                'unrealized_pl': float(pos.unrealized_pl),
                'unrealized_plpc': float(pos.unrealized_plpc)
            } for pos in positions]
            
            logger.info(f"Positions formatted: {formatted_positions}")
            return formatted_positions
        except Exception as e:
            logger.error(f"Error getting positions: {e}", exc_info=True)
            return []

    def get_historical_data(self, symbol, timeframe=TimeFrame.Day, limit=100):
        """Get historical price data for a symbol"""
        try:
            # Get current time and calculate start time
            end = datetime.now()
            start = end - timedelta(days=limit)
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=timeframe,
                start=start,
                end=end
            )
            bars = self.data_client.get_stock_bars(request)
            
            if not bars or symbol not in bars:
                logger.error(f"No data returned for {symbol}")
                return None
                
            # Convert to pandas DataFrame
            df = pd.DataFrame([{
                'timestamp': bar.timestamp,
                'open': float(bar.open),
                'high': float(bar.high),
                'low': float(bar.low),
                'close': float(bar.close),
                'volume': int(bar.volume)
            } for bar in bars[symbol]])
            
            if len(df) > 0:
                df.set_index('timestamp', inplace=True)
                df.sort_index(inplace=True)
                logger.info(f"Retrieved {len(df)} bars of historical data for {symbol}")
            else:
                logger.warning(f"No historical data found for {symbol}")
                
            return df
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return None

    def place_market_order(self, symbol, qty, side='buy'):
        """Place a market order"""
        try:
            order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
            
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=TimeInForce.DAY
            )
            
            order = self.trading_client.submit_order(order_request)
            logger.info(f"Placed {side} order for {qty} shares of {symbol}")
            return order
            
        except Exception as e:
            logger.error(f"Error placing order for {symbol}: {e}")
            return None

    def get_account_info(self):
        """Get detailed account information"""
        try:
            account = self.trading_client.get_account()
            return {
                'id': account.id,
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'buying_power': float(account.buying_power),
                'initial_margin': float(account.initial_margin),
                'maintenance_margin': float(account.maintenance_margin),
                'daytrade_count': account.daytrade_count,
                'last_equity': float(account.last_equity),
                'status': account.status
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None

    def get_portfolio_analysis(self):
        """Get detailed portfolio analysis including performance metrics"""
        try:
            positions = self.get_positions()
            account = self.get_account_info()
            
            if not positions or not account:
                return None
                
            # Calculate portfolio metrics
            total_market_value = float(account['portfolio_value'])
            total_pl = sum(pos['unrealized_pl'] for pos in positions)
            
            # Calculate position-specific metrics
            position_analysis = []
            for pos in positions:
                market_value = float(pos['market_value'])
                weight = (market_value / total_market_value) * 100
                pl_pct = float(pos['unrealized_plpc']) * 100
                
                position_analysis.append({
                    'symbol': pos['symbol'],
                    'shares': float(pos['qty']),
                    'market_value': market_value,
                    'weight': weight,
                    'entry_price': float(pos['avg_entry_price']),
                    'current_price': float(pos['current_price']),
                    'pl_dollars': float(pos['unrealized_pl']),
                    'pl_percent': pl_pct
                })
            
            # Sort positions by market value (weight)
            position_analysis.sort(key=lambda x: x['market_value'], reverse=True)
            
            # Calculate portfolio concentration
            top_5_weight = sum(pos['weight'] for pos in position_analysis[:5])
            
            # Performance metrics
            winners = [pos for pos in position_analysis if pos['pl_percent'] > 0]
            losers = [pos for pos in position_analysis if pos['pl_percent'] <= 0]
            
            avg_winner = sum(pos['pl_percent'] for pos in winners) / len(winners) if winners else 0
            avg_loser = sum(pos['pl_percent'] for pos in losers) / len(losers) if losers else 0
            
            # Risk metrics
            max_gain = max(pos['pl_percent'] for pos in position_analysis)
            max_loss = min(pos['pl_percent'] for pos in position_analysis)
            
            analysis = {
                'portfolio_value': total_market_value,
                'cash': float(account['cash']),
                'buying_power': float(account['buying_power']),
                'total_pl': total_pl,
                'positions_count': len(positions),
                'winning_positions': len(winners),
                'losing_positions': len(losers),
                'avg_winner_return': avg_winner,
                'avg_loser_return': avg_loser,
                'max_position_gain': max_gain,
                'max_position_loss': max_loss,
                'top_5_concentration': top_5_weight,
                'positions': position_analysis
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing portfolio: {e}")
            return None

    def get_portfolio_summary(self):
        """Get portfolio summary data"""
        logger.debug("Fetching portfolio summary...")
        retry_count = 3
        retry_delay = 1

        for attempt in range(retry_count):
            try:
                # Get account information
                logger.debug(f"Getting account information (attempt {attempt + 1}/{retry_count})...")
                account = self.trading_client.get_account()
                logger.debug(f"Account info received: {account}")
                
                # Get all positions
                logger.debug(f"Getting positions (attempt {attempt + 1}/{retry_count})...")
                positions = self.trading_client.get_all_positions()
                logger.debug(f"Retrieved {len(positions)} positions")
                
                # Calculate total P&L
                total_pl = sum(float(pos.unrealized_pl) for pos in positions)
                logger.debug(f"Total P&L calculated: {total_pl}")
                
                # Calculate daily P&L
                daily_pl = float(account.equity) - float(account.last_equity)
                logger.debug(f"Daily P&L calculated: {daily_pl}")
                
                summary = {
                    'portfolio_value': float(account.portfolio_value),
                    'cash': float(account.cash),
                    'buying_power': float(account.buying_power),
                    'total_pl': total_pl,
                    'daily_pl': daily_pl,
                    'daily_pl_percent': (daily_pl / float(account.last_equity)) * 100 if float(account.last_equity) != 0 else 0,
                    'positions_count': len(positions),
                    'status': account.status,
                    'timestamp': datetime.now().isoformat(),
                    'last_update_successful': True
                }
                
                logger.info(f"Portfolio summary generated: {summary}")
                return summary
                
            except Exception as e:
                logger.error(f"Error getting portfolio summary (attempt {attempt + 1}/{retry_count}): {e}", exc_info=True)
                if attempt < retry_count - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    return {
                        'error': str(e),
                        'last_update_successful': False,
                        'timestamp': datetime.now().isoformat()
                    }

    def print_portfolio_summary(self):
        """Print a formatted summary of the portfolio analysis"""
        try:
            analysis = self.get_portfolio_analysis()
            if not analysis:
                logger.error("Could not generate portfolio analysis")
                return
            
            logger.info("\n=== Portfolio Summary ===")
            logger.info(f"Portfolio Value: ${analysis['portfolio_value']:,.2f}")
            logger.info(f"Cash: ${analysis['cash']:,.2f}")
            logger.info(f"Buying Power: ${analysis['buying_power']:,.2f}")
            logger.info(f"Total P/L: ${analysis['total_pl']:,.2f}")
            
            logger.info("\n=== Position Statistics ===")
            logger.info(f"Total Positions: {analysis['positions_count']}")
            logger.info(f"Winning Positions: {analysis['winning_positions']} "
                      f"({analysis['winning_positions']/analysis['positions_count']*100:.1f}%)")
            logger.info(f"Average Winner: {analysis['avg_winner_return']:+.2f}%")
            logger.info(f"Average Loser: {analysis['avg_loser_return']:+.2f}%")
            logger.info(f"Best Position: {analysis['max_position_gain']:+.2f}%")
            logger.info(f"Worst Position: {analysis['max_position_loss']:+.2f}%")
            
            logger.info("\n=== Portfolio Concentration ===")
            logger.info(f"Top 5 Positions Weight: {analysis['top_5_concentration']:.1f}%")
            
            logger.info("\n=== Top 5 Positions by Size ===")
            for pos in analysis['positions'][:5]:
                logger.info(f"{pos['symbol']}: ${pos['market_value']:,.2f} "
                          f"({pos['weight']:.1f}% of portfolio, {pos['pl_percent']:+.2f}% P/L)")
            
            logger.info("\n=== Best Performing Positions ===")
            best = sorted(analysis['positions'], key=lambda x: x['pl_percent'], reverse=True)[:3]
            for pos in best:
                logger.info(f"{pos['symbol']}: {pos['pl_percent']:+.2f}% "
                          f"(${pos['pl_dollars']:,.2f})")
            
            logger.info("\n=== Worst Performing Positions ===")
            worst = sorted(analysis['positions'], key=lambda x: x['pl_percent'])[:3]
            for pos in worst:
                logger.info(f"{pos['symbol']}: {pos['pl_percent']:+.2f}% "
                          f"(${pos['pl_dollars']:,.2f})")
                
        except Exception as e:
            logger.error(f"Error printing portfolio summary: {e}")

    def create_portfolio_visualizations(self):
        """Create interactive portfolio visualizations using Plotly"""
        try:
            import plotly.graph_objects as go
            import plotly.express as px
            from plotly.subplots import make_subplots
            import os
            
            analysis = self.get_portfolio_analysis()
            if not analysis:
                logger.error("Could not generate portfolio analysis for visualization")
                return
                
            # Create output directory if specified
            output_dir = None
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # 1. Portfolio Composition Treemap
            positions_df = pd.DataFrame(analysis['positions'])
            fig_treemap = px.treemap(
                positions_df,
                values='market_value',
                path=[px.Constant("Portfolio"), 'symbol'],
                color='pl_percent',
                color_continuous_scale='RdYlGn',
                title='Portfolio Composition and Performance',
                custom_data=['shares', 'entry_price', 'current_price', 'pl_dollars']
            )
            fig_treemap.update_traces(
                hovertemplate="""
                <b>%{label}</b><br>
                Value: $%{value:,.2f}<br>
                Shares: %{customdata[0]:.0f}<br>
                Entry: $%{customdata[1]:.2f}<br>
                Current: $%{customdata[2]:.2f}<br>
                P/L: $%{customdata[3]:+,.2f} (%{color:+.2f}%)<br>
                <extra></extra>
                """
            )
            
            # 2. Performance Distribution
            fig_dist = go.Figure()
            fig_dist.add_trace(go.Histogram(
                x=positions_df['pl_percent'],
                name='P/L Distribution',
                nbinsx=20,
                marker_color='lightblue'
            ))
            fig_dist.update_layout(
                title='Distribution of Position Returns',
                xaxis_title='Return (%)',
                yaxis_title='Number of Positions',
                showlegend=False
            )
            
            # 3. Top Winners and Losers
            fig_wl = make_subplots(
                rows=1, cols=2,
                subplot_titles=('Top 5 Winners', 'Top 5 Losers'),
                specs=[[{'type': 'bar'}, {'type': 'bar'}]]
            )
            
            # Winners
            winners = positions_df.nlargest(5, 'pl_percent')
            fig_wl.add_trace(
                go.Bar(
                    x=winners['symbol'],
                    y=winners['pl_percent'],
                    marker_color='green',
                    name='Winners'
                ),
                row=1, col=1
            )
            
            # Losers
            losers = positions_df.nsmallest(5, 'pl_percent')
            fig_wl.add_trace(
                go.Bar(
                    x=losers['symbol'],
                    y=losers['pl_percent'],
                    marker_color='red',
                    name='Losers'
                ),
                row=1, col=2
            )
            
            fig_wl.update_layout(
                title='Top Winners and Losers',
                showlegend=False,
                yaxis_title='Return (%)',
                yaxis2_title='Return (%)'
            )
            
            # 4. Position Sizes Pie Chart
            fig_pie = go.Figure(data=[go.Pie(
                labels=positions_df['symbol'],
                values=positions_df['market_value'],
                hole=.3,
                textinfo='label+percent',
                hovertemplate="""
                <b>%{label}</b><br>
                Value: $%{value:,.2f}<br>
                Portfolio: %{percent}<br>
                <extra></extra>
                """
            )])
            fig_pie.update_layout(title='Portfolio Allocation')
            
            # Save all figures if output directory is specified
            if output_dir:
                fig_treemap.write_html(os.path.join(output_dir, 'portfolio_treemap.html'))
                fig_dist.write_html(os.path.join(output_dir, 'return_distribution.html'))
                fig_wl.write_html(os.path.join(output_dir, 'winners_losers.html'))
                fig_pie.write_html(os.path.join(output_dir, 'portfolio_allocation.html'))
                
                logger.info(f"\nVisualization files saved to: {output_dir}")
                logger.info("Files created:")
                logger.info("1. portfolio_treemap.html - Interactive treemap of portfolio composition")
                logger.info("2. return_distribution.html - Distribution of position returns")
                logger.info("3. winners_losers.html - Top winners and losers comparison")
                logger.info("4. portfolio_allocation.html - Portfolio allocation pie chart")
            
            return {
                'treemap': fig_treemap,
                'distribution': fig_dist,
                'winners_losers': fig_wl,
                'allocation': fig_pie
            }
            
        except Exception as e:
            logger.error(f"Error creating portfolio visualizations: {e}")
            return None

    def get_recent_trades(self, limit=50):
        """Get recent trades"""
        try:
            logger.debug(f"Fetching {limit} recent trades...")
            
            # Get all orders
            trades = self.trading_client.get_orders()
            
            if not trades:
                logger.warning("No trades found")
                return []
            
            # Filter and format the trades
            formatted_trades = []
            for trade in trades[:limit]:  # Limit the number of trades manually
                if trade.status == 'filled':  # Only include filled orders
                    formatted_trade = {
                        'id': trade.id,
                        'symbol': trade.symbol,
                        'side': trade.side,
                        'qty': float(trade.filled_qty),
                        'filled_price': float(trade.filled_avg_price) if trade.filled_avg_price else 0.0,
                        'timestamp': trade.filled_at.isoformat() if trade.filled_at else None,
                        'type': trade.type,
                        'status': trade.status
                    }
                    formatted_trades.append(formatted_trade)
            
            logger.info(f"Retrieved {len(formatted_trades)} trades")
            return formatted_trades[:limit]  # Ensure we don't exceed the limit
            
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}", exc_info=True)
            return []
