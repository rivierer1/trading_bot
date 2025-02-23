import logging
import os
from dotenv import load_dotenv
from alpaca_client import AlpacaClient
from twitter_client import TwitterClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_environment_variables():
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

def main():
    """Test connections to all APIs"""
    load_dotenv()
    
    if not check_environment_variables():
        return
    
    # Test Alpaca connection
    logger.info("\n=== Testing Alpaca API Connection ===")
    try:
        alpaca = AlpacaClient()
        if alpaca.test_connection():
            logger.info("✓ Alpaca API connection successful")
            
            # Get some test data
            positions = alpaca.get_positions()
            logger.info(f"\nCurrent positions ({len(positions)}):")
            for pos in positions:
                pl_pct = pos['unrealized_plpc'] * 100
                logger.info(f"{pos['symbol']}: {pos['qty']} shares @ ${pos['avg_entry_price']:.2f} "
                          f"(Current: ${pos['current_price']:.2f}, P/L: {pl_pct:+.2f}%)")
            
            # Print detailed portfolio analysis
            alpaca.print_portfolio_summary()
            
            # Generate portfolio visualizations
            logger.info("\nGenerating portfolio visualizations...")
            viz_dir = os.path.join(os.getcwd(), 'portfolio_analysis')
            alpaca.create_portfolio_visualizations(viz_dir)
            
            # Get AAPL historical data (commented out for now as it needs fixing)
            # aapl_data = alpaca.get_historical_data('AAPL', limit=5)
            # if aapl_data is not None:
            #     logger.info("\nLatest AAPL data:")
            #     logger.info(aapl_data.tail(1))
        else:
            logger.error("✗ Failed to connect to Alpaca API")
    except Exception as e:
        logger.error(f"✗ Error testing Alpaca connection: {e}")
    
    # Test Twitter connection
    logger.info("\n=== Testing Twitter API Connection ===")
    try:
        twitter = TwitterClient()
        if twitter.test_connection():
            logger.info("✓ Twitter API connection successful")
        else:
            logger.error("✗ Failed to connect to Twitter API")
    except Exception as e:
        logger.error(f"✗ Error testing Twitter connection: {e}")

if __name__ == "__main__":
    main()
