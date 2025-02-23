import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_env_vars():
    """Check if all required environment variables are set"""
    required_vars = [
        'ALPACA_API_KEY',
        'ALPACA_API_SECRET',
        'TWITTER_BEARER_TOKEN'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in your .env file")
        return False
    return True

def test_alpaca_connection():
    """Test connection to Alpaca API and verify data access"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get API credentials
        api_key = os.getenv('ALPACA_API_KEY')
        api_secret = os.getenv('ALPACA_API_SECRET')
        base_url = 'https://paper-api.alpaca.markets' if os.getenv('ALPACA_PAPER_TRADING', 'True').lower() == 'true' else 'https://api.alpaca.markets'
        
        logger.info("Testing Alpaca API connection...")
        logger.info(f"Using base URL: {base_url}")
        
        # Initialize Alpaca API
        api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')
        
        # Test account information
        account = api.get_account()
        logger.info("Account Information:")
        logger.info(f"Account ID: {account.id}")
        logger.info(f"Account Status: {account.status}")
        logger.info(f"Portfolio Value: ${account.portfolio_value}")
        logger.info(f"Cash: ${account.cash}")
        logger.info(f"Buying Power: ${account.buying_power}")
        
        # Test positions
        positions = api.list_positions()
        logger.info("\nCurrent Positions:")
        for position in positions:
            logger.info(f"{position.symbol}: {position.qty} shares @ ${position.avg_entry_price}")
        
        # Test recent trades
        trades = api.get_trades('AAPL', '2024-02-23', '2024-02-23', limit=5)
        logger.info("\nRecent AAPL Trades (Sample):")
        for trade in trades:
            logger.info(f"Time: {trade.t}, Price: ${trade.p}, Size: {trade.s}")
        
        return True, "Alpaca connection test successful"
        
    except Exception as e:
        logger.error(f"Error testing Alpaca connection: {str(e)}")
        return False, str(e)

def main():
    """Test connections to all APIs"""
    load_dotenv()
    
    if not check_env_vars():
        return
    
    # Test Alpaca connection
    logger.info("\n=== Testing Alpaca API Connection ===")
    success, message = test_alpaca_connection()
    if success:
        logger.info("✓ Alpaca API connection successful")
    else:
        logger.error(f"✗ {message}")

if __name__ == "__main__":
    main()
