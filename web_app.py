from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from trading_bot import TradingBot
from config import TradingConfig
from auth import User, init_admin_account
from alpaca_client import AlpacaClient
import threading
import queue
import json
from datetime import datetime
import os
from dotenv import load_dotenv, set_key
from twitter_client import TwitterClient
from ai_analyzer import AIAnalyzer
import logging
from market_data_service import MarketDataService

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key')

# Configure Socket.IO with async mode and logging
socketio = SocketIO(
    app, 
    async_mode='threading',
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True
)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(username):
    return User.get(username)

# Initialize services
try:
    logger.info("Initializing services...")
    market_data = MarketDataService()
    alpaca = AlpacaClient()
    logger.info("Services initialized successfully")
except Exception as e:
    logger.error(f"Error initializing services: {e}")
    raise

# Global variables
bot = None
bot_thread = None
is_bot_running = False
update_queue = queue.Queue()

def load_config():
    """Load configuration from .env file"""
    config = {}
    env_file = '.env'
    
    # Load from .env file first
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    config[key] = value
    
    # Then load from environment variables to ensure we have the latest values
    env_vars = [
        'TWITTER_API_KEY',
        'TWITTER_API_SECRET',
        'TWITTER_BEARER_TOKEN',
        'OPENAI_API_KEY',
        'TOS_API_KEY',
        'TOS_REDIRECT_URI',
        'TOS_ACCOUNT_ID',
        'MAX_POSITION_SIZE',
        'STOP_LOSS_PERCENTAGE',
        'TAKE_PROFIT_PERCENTAGE',
        'TRADING_SYMBOLS'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value is not None:
            config[var] = value
    
    return config

def save_config(settings):
    """Save configuration to .env file"""
    logger.info("Received settings request: %s", settings)
    
    env_file = '.env'
    
    # Load existing config first
    existing_config = {}
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    existing_config[key] = value
    logger.info("Existing config: %s", existing_config)
    
    # Ensure we have the admin credentials
    admin_config = {
        'ADMIN_USERNAME': os.getenv('ADMIN_USERNAME', ''),
        'ADMIN_PASSWORD_HASH': os.getenv('ADMIN_PASSWORD_HASH', '')
    }
    
    # Update existing config with new settings
    for key, value in settings.items():
        if isinstance(value, str) and value.strip():  # Check if value is string and not empty
            # Special handling for Twitter credentials
            if key in ['TWITTER_API_KEY', 'TWITTER_API_SECRET', 'TWITTER_BEARER_TOKEN']:
                logger.info("Updating %s", key)
                existing_config[key.upper()] = value.strip()
            else:
                existing_config[key.upper()] = value.strip()
    
    # Create .env content
    env_content = []
    
    # Add admin credentials first
    for key in ['ADMIN_USERNAME', 'ADMIN_PASSWORD_HASH']:
        if key in existing_config:
            env_content.append(f"{key}={existing_config[key]}")
    
    # Add all other settings
    for key, value in existing_config.items():
        if key not in ['ADMIN_USERNAME', 'ADMIN_PASSWORD_HASH']:
            env_content.append(f"{key}={value}")
    
    logger.info("Writing config: %s", env_content)
    
    # Write all content to .env file
    with open(env_file, 'w') as f:
        f.write('\n'.join(env_content) + '\n')  # Add newline at end of file
    
    # Force reload of environment variables
    load_dotenv(override=True)
    
    # Return the current config
    return {key: os.getenv(key, '') for key in existing_config.keys()}

def background_thread():
    """Background thread for sending updates to clients"""
    logger.info("Starting background thread for updates...")
    thread_id = threading.get_ident()
    logger.debug("Background thread ID: %s", thread_id)
    
    while True:
        try:
            # Update portfolio data every 30 seconds
            logger.debug("Fetching portfolio summary...")
            portfolio_summary = alpaca.get_portfolio_summary()
            if portfolio_summary:
                logger.debug("Emitting portfolio update: %s", portfolio_summary)
                socketio.emit('portfolio_update', portfolio_summary)
            else:
                logger.warning("No portfolio summary data available")
            
            logger.debug("Fetching positions...")
            positions = alpaca.get_positions()
            if positions:
                logger.debug("Emitting positions update: %s", positions)
                socketio.emit('positions_update', positions)
            else:
                logger.warning("No positions data available")
            
            # Get recent trades
            logger.debug("Fetching recent trades...")
            trades = alpaca.get_recent_trades()
            if trades:
                formatted_trades = [format_trade_data(trade) for trade in trades]
                logger.debug("Emitting trades update: %s", formatted_trades)
                socketio.emit('trades_update', formatted_trades)
            else:
                logger.warning("No recent trades data available")
            
            # Process any other updates in the queue
            while not update_queue.empty():
                update = update_queue.get()
                event_type = update.get('type')
                data = update.get('data')
                logger.debug("Emitting queued update - type: %s, data: %s", event_type, data)
                socketio.emit(event_type, data)
                
        except Exception as e:
            logger.error("Error in background thread: %s", e, exc_info=True)
        
        logger.debug("Sleeping for 30 seconds...")
        socketio.sleep(30)

@app.route('/')
@login_required
def dashboard():
    """Render dashboard page"""
    logger.debug("Rendering dashboard page")
    return render_template('dashboard.html')

@app.route('/trades')
@login_required
def trades():
    """Render trades page"""
    logger.debug("Rendering trades page")
    return render_template('trades.html')

@app.route('/settings')
@login_required
def settings():
    """Render settings page"""
    logger.debug("Rendering settings page")
    config = load_config()
    return render_template('settings.html', config=config)

@app.route('/test_sentiment')
@login_required
def test_sentiment_page():
    """Render test sentiment page"""
    logger.debug("Rendering test sentiment page")
    return render_template('test_sentiment.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login request"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        user = User.get(username)
        if user and User.verify_password(password):
            login_user(user, remember=remember)
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password')
    logger.debug("Rendering login page")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Handle logout request"""
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/settings', methods=['POST', 'GET'])
@login_required
def update_settings():
    """Handle update settings request"""
    if request.method == 'POST':
        try:
            settings = request.json
            if not settings:
                return jsonify({'status': 'error', 'message': 'No settings provided'}), 400
            
            logger.info("Received settings request: %s", {k: '***' if 'TOKEN' in k.upper() or 'KEY' in k.upper() or 'SECRET' in k.upper() else v for k, v in settings.items()})
                
            # Save config and get updated values
            updated_config = save_config(settings)
            
            # Hide sensitive data in logs
            safe_config = {k: '***' if 'TOKEN' in k.upper() or 'KEY' in k.upper() or 'SECRET' in k.upper() else v for k, v in updated_config.items()}
            logger.info("Updated config: %s", safe_config)
            
            # Initialize a new Twitter client to test the credentials
            try:
                twitter = TwitterClient()
                test_tweets = twitter.get_tweets(['AAPL'], hours_lookback=1, max_tweets=1)
                if test_tweets:
                    logger.info("Successfully tested Twitter API connection")
            except Exception as e:
                logger.warning("Could not test Twitter connection: %s", str(e))
            
            return jsonify({
                'status': 'success',
                'config': updated_config
            })
        except Exception as e:
            logger.error("Error in update_settings: %s", str(e))
            return jsonify({'status': 'error', 'message': str(e)}), 500
    else:
        config = load_config()
        # Hide sensitive data
        safe_config = {k: '***' if 'TOKEN' in k.upper() or 'KEY' in k.upper() or 'SECRET' in k.upper() else v for k, v in config.items()}
        return jsonify({
            'status': 'success',
            'config': config
        })

@app.route('/api/test_sentiment', methods=['GET'])
@login_required
def test_sentiment():
    """Handle test sentiment request"""
    try:
        # Initialize clients
        twitter = TwitterClient()
        analyzer = AIAnalyzer()
        
        # Get tweets about a test symbol - reduced number of tweets and lookback period
        symbol = request.args.get('symbol', 'AAPL')  # Default to AAPL if no symbol provided
        logger.info("Testing sentiment for symbol: %s", symbol)
        
        # Only look back 30 minutes and get 1 tweet
        tweets = twitter.get_tweets(
            keywords=[symbol], 
            hours_lookback=0.5,  # 30 minutes
            max_tweets=1  # Just get 1 tweet for testing
        )
        
        # Get tweet texts
        tweet_texts = [tweet.text for tweet in tweets] if tweets else []
        
        if not tweet_texts:
            logger.warning("No tweets found for symbol: %s", symbol)
            return jsonify({
                'symbol': symbol,
                'sentiment_score': 0,
                'tweets': [],
                'tweet_count': 0,
                'message': 'No tweets found for this symbol'
            })
        
        # Analyze sentiment
        logger.info("Analyzing sentiment for %s tweets", len(tweet_texts))
        sentiment = analyzer.analyze_sentiment(tweet_texts)
        logger.info("Sentiment score: %s", sentiment)
        
        return jsonify({
            'symbol': symbol,
            'sentiment_score': sentiment,
            'tweets': tweet_texts,
            'tweet_count': len(tweet_texts)
        })
    except Exception as e:
        error_msg = str(e)
        if "Rate limit" in error_msg:
            error_msg = "Twitter API rate limit exceeded. Please wait a few minutes and try again."
        logger.error("Error in test_sentiment: %s", error_msg)
        return jsonify({'error': error_msg}), 429 if "Rate limit" in str(e) else 500

@app.route('/api/market/snapshot', methods=['GET'])
@login_required
def get_market_snapshot():
    """Handle get market snapshot request"""
    try:
        symbols = request.args.get('symbols', 'SPY,QQQ,DIA').split(',')
        snapshot = market_data.get_market_snapshot(symbols)
        return jsonify(snapshot)
    except Exception as e:
        logger.error("Error getting market snapshot: %s", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/technical/<symbol>', methods=['GET'])
@login_required
def get_technical_data(symbol):
    """Handle get technical data request"""
    try:
        days = int(request.args.get('days', '5'))
        indicators = market_data.get_technical_indicators(symbol, days)
        return jsonify(indicators)
    except Exception as e:
        logger.error("Error getting technical indicators: %s", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/breadth', methods=['GET'])
@login_required
def get_market_breadth():
    """Handle get market breadth request"""
    try:
        breadth = market_data.get_market_breadth()
        return jsonify(breadth)
    except Exception as e:
        logger.error("Error getting market breadth: %s", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/vwap/<symbol>', methods=['GET'])
@login_required
def get_vwap(symbol):
    """Handle get VWAP request"""
    try:
        vwap = market_data.get_intraday_vwap(symbol)
        return jsonify({'vwap': vwap})
    except Exception as e:
        logger.error("Error getting VWAP: %s", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/status', methods=['GET'])
@login_required
def get_market_status():
    """Handle get market status request"""
    try:
        is_open = market_data.is_market_open()
        return jsonify({'is_open': is_open})
    except Exception as e:
        logger.error("Error getting market status: %s", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio/summary')
@login_required
def get_portfolio_summary():
    """Handle get portfolio summary request"""
    try:
        logger.info("Fetching portfolio summary...")
        analysis = alpaca.get_portfolio_analysis()
        if not analysis:
            logger.error("Portfolio analysis returned None")
            return jsonify({'error': 'Failed to get portfolio analysis'}), 500
        logger.info("Portfolio summary: %s", analysis)
        return jsonify(analysis)
    except Exception as e:
        logger.error("Error fetching portfolio summary: %s", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio/positions')
@login_required
def get_positions():
    """Handle get positions request"""
    try:
        positions = alpaca.get_positions()
        return jsonify(positions)
    except Exception as e:
        logger.error("Error fetching positions: %s", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio/charts')
@login_required
def get_portfolio_charts():
    """Handle get portfolio charts request"""
    try:
        logger.info("Generating portfolio charts...")
        charts = alpaca.create_portfolio_visualizations()
        if not charts:
            logger.error("Portfolio charts returned None")
            return jsonify({'error': 'Could not generate charts'}), 500
        logger.info("Successfully generated portfolio charts")
        
        # Convert Plotly figures to JSON
        chart_data = {
            'treemap': charts['treemap'].to_json(),
            'distribution': charts['distribution'].to_json(),
            'winners_losers': charts['winners_losers'].to_json(),
            'allocation': charts['allocation'].to_json()
        }
        return jsonify(chart_data)
    except Exception as e:
        logger.error("Error generating charts: %s", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/trades/recent')
@login_required
def get_recent_trades():
    """Handle get recent trades request"""
    try:
        trades = alpaca.get_recent_trades()
        return jsonify(trades)
    except Exception as e:
        logger.error("Error fetching recent trades: %s", str(e))
        return jsonify({'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("Client connected: %s", request.sid)
    global bot_thread
    if bot_thread is None:
        bot_thread = socketio.start_background_task(background_thread)
    emit('connection_response', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("Client disconnected: %s", request.sid)

@socketio.on('start_bot')
def handle_start_bot():
    """Handle start bot request"""
    global bot, is_bot_running
    if not is_bot_running:
        config = TradingConfig()
        bot = TradingBot(config)
        is_bot_running = True
        
        def bot_update_handler(update_type, data):
            update_queue.put({
                'type': f'{update_type}_update',
                'data': data
            })
        
        bot.set_update_handler(bot_update_handler)
        threading.Thread(target=bot.start, daemon=True).start()
        emit('bot_status', {'status': 'running'})

@socketio.on('stop_bot')
def handle_stop_bot():
    """Handle stop bot request"""
    global bot, is_bot_running
    if is_bot_running and bot:
        bot.stop()
        is_bot_running = False
        emit('bot_status', {'status': 'stopped'})

def format_trade_data(trade):
    return {
        'time': trade.timestamp.isoformat(),
        'symbol': trade.symbol,
        'action': trade.action,
        'quantity': trade.quantity,
        'price': float(trade.price),
        'sentimentScore': float(trade.sentiment_score)
    }

if __name__ == '__main__':
    # Initialize admin account if it doesn't exist
    init_admin_account()
    
    # Start background thread
    thread = threading.Thread(target=background_thread)
    thread.daemon = True
    thread.start()
    
    # Start the Flask-SocketIO server
    socketio.run(app, 
                host='127.0.0.1',  # Only allow local connections
                port=5002,  # Use a different port
                debug=True,
                use_reloader=False,  # Disable reloader in debug mode
                allow_unsafe_werkzeug=True)
