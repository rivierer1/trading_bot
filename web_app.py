from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from trading_bot import TradingBot
from config import TradingConfig
from auth import User, init_admin_account
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

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key')  # Change this in production
socketio = SocketIO(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(username):
    return User.get(username)

# Initialize services
market_data = MarketDataService()

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
    print("Received settings:", settings)  # Debug log
    
    env_file = '.env'
    
    # Load existing config first
    existing_config = {}
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    existing_config[key] = value
    print("Existing config:", existing_config)  # Debug log
    
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
                print(f"Updating {key}")  # Debug log
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
    
    print("Writing config:", env_content)  # Debug log
    
    # Write all content to .env file
    with open(env_file, 'w') as f:
        f.write('\n'.join(env_content) + '\n')  # Add newline at end of file
    
    # Force reload of environment variables
    load_dotenv(override=True)
    
    # Return the current config
    return {key: os.getenv(key, '') for key in existing_config.keys()}

def background_thread():
    """Background thread for sending updates to clients"""
    while True:
        if not update_queue.empty():
            update = update_queue.get()
            event_type = update.get('type')
            data = update.get('data')
            socketio.emit(event_type, data)
        socketio.sleep(0.1)

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/trades')
@login_required
def trades():
    return render_template('trades.html')

@app.route('/settings')
@login_required
def settings():
    config = load_config()
    return render_template('settings.html', config=config)

@app.route('/test_sentiment')
@login_required
def test_sentiment_page():
    return render_template('test_sentiment.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        user = User.get(username)
        if user and User.verify_password(password):
            login_user(user, remember=remember)
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/settings', methods=['POST', 'GET'])
@login_required
def update_settings():
    if request.method == 'POST':
        try:
            settings = request.json
            if not settings:
                return jsonify({'status': 'error', 'message': 'No settings provided'}), 400
            
            print("Received settings request:", {k: '***' if 'TOKEN' in k.upper() or 'KEY' in k.upper() or 'SECRET' in k.upper() else v for k, v in settings.items()})  # Debug log but hide sensitive data
                
            # Save config and get updated values
            updated_config = save_config(settings)
            
            # Hide sensitive data in logs
            safe_config = {k: '***' if 'TOKEN' in k.upper() or 'KEY' in k.upper() or 'SECRET' in k.upper() else v for k, v in updated_config.items()}
            print("Updated config:", safe_config)  # Debug log
            
            # Initialize a new Twitter client to test the credentials
            try:
                twitter = TwitterClient()
                test_tweets = twitter.get_tweets(['AAPL'], hours_lookback=1, max_tweets=1)
                if test_tweets:
                    print("Successfully tested Twitter API connection")
            except Exception as e:
                print(f"Warning: Could not test Twitter connection: {str(e)}")
            
            return jsonify({
                'status': 'success',
                'config': updated_config
            })
        except Exception as e:
            print(f"Error in update_settings: {str(e)}")
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
    try:
        # Initialize clients
        twitter = TwitterClient()
        analyzer = AIAnalyzer()
        
        # Get tweets about a test symbol - reduced number of tweets and lookback period
        symbol = request.args.get('symbol', 'AAPL')  # Default to AAPL if no symbol provided
        logging.info(f"Testing sentiment for symbol: {symbol}")
        
        # Only look back 30 minutes and get 1 tweet
        tweets = twitter.get_tweets(
            keywords=[symbol], 
            hours_lookback=0.5,  # 30 minutes
            max_tweets=1  # Just get 1 tweet for testing
        )
        
        # Get tweet texts
        tweet_texts = [tweet.text for tweet in tweets] if tweets else []
        
        if not tweet_texts:
            logging.warning(f"No tweets found for symbol: {symbol}")
            return jsonify({
                'symbol': symbol,
                'sentiment_score': 0,
                'tweets': [],
                'tweet_count': 0,
                'message': 'No tweets found for this symbol'
            })
        
        # Analyze sentiment
        logging.info(f"Analyzing sentiment for {len(tweet_texts)} tweets")
        sentiment = analyzer.analyze_sentiment(tweet_texts)
        logging.info(f"Sentiment score: {sentiment}")
        
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
        logging.error(f"Error in test_sentiment: {error_msg}")
        return jsonify({'error': error_msg}), 429 if "Rate limit" in str(e) else 500

@app.route('/api/market/snapshot', methods=['GET'])
@login_required
def get_market_snapshot():
    try:
        symbols = request.args.get('symbols', 'SPY,QQQ,DIA').split(',')
        snapshot = market_data.get_market_snapshot(symbols)
        return jsonify(snapshot)
    except Exception as e:
        logging.error(f"Error getting market snapshot: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/technical/<symbol>', methods=['GET'])
@login_required
def get_technical_data(symbol):
    try:
        days = int(request.args.get('days', '5'))
        indicators = market_data.get_technical_indicators(symbol, days)
        return jsonify(indicators)
    except Exception as e:
        logging.error(f"Error getting technical indicators: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/breadth', methods=['GET'])
@login_required
def get_market_breadth():
    try:
        breadth = market_data.get_market_breadth()
        return jsonify(breadth)
    except Exception as e:
        logging.error(f"Error getting market breadth: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/vwap/<symbol>', methods=['GET'])
@login_required
def get_vwap(symbol):
    try:
        vwap = market_data.get_intraday_vwap(symbol)
        return jsonify({'vwap': vwap})
    except Exception as e:
        logging.error(f"Error getting VWAP: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/status', methods=['GET'])
@login_required
def get_market_status():
    try:
        is_open = market_data.is_market_open()
        return jsonify({'is_open': is_open})
    except Exception as e:
        logging.error(f"Error getting market status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    global bot_thread
    if bot_thread is None:
        bot_thread = socketio.start_background_task(background_thread)

@socketio.on('start_bot')
def handle_start_bot():
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
    
    # Get port from environment variable or use default
    port = int(os.getenv('PORT', 5000))
    
    # Get host from environment variable or use default
    host = os.getenv('HOST', '0.0.0.0')
    
    # SSL context for HTTPS (optional but recommended for production)
    ssl_context = None
    cert_path = os.getenv('SSL_CERT_PATH')
    key_path = os.getenv('SSL_KEY_PATH')
    
    if cert_path and key_path:
        ssl_context = (cert_path, key_path)
    
    print(f"Starting server on {host}:{port}")
    print("Access the application at:")
    print(f"Local: http://localhost:{port}")
    print(f"Network: http://<your-ip-address>:{port}")
    
    logging.basicConfig(level=logging.INFO)
    
    socketio.run(app, 
                 host=host, 
                 port=port, 
                 debug=False,  # Set to False for production
                 ssl_context=ssl_context,
                 allow_unsafe_werkzeug=True)  # Only for development
