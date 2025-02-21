import os
from tos_client import ThinkOrSwimClient
import logging
from dotenv import load_dotenv, find_dotenv, dotenv_values

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_market_data():
    # Load and verify environment variables
    dotenv_path = find_dotenv()
    logger.info(f"Found .env file at: {dotenv_path}")
    
    # Try to read raw values first
    logger.info("\nRaw .env values:")
    logger.info("-" * 40)
    env_values = dotenv_values(dotenv_path)
    for key, value in env_values.items():
        if 'SECRET' in key:
            logger.info(f"{key}: ***")
        else:
            logger.info(f"{key}: {value}")
    logger.info("-" * 40)
    
    # Now load into environment
    load_dotenv(dotenv_path)
    logger.info("\nEnvironment variables after load_dotenv:")
    logger.info("-" * 40)
    for key in ['TOS_API_KEY', 'TOS_API_SECRET', 'TOS_ACCOUNT_ID', 'TOS_REDIRECT_URI']:
        value = os.getenv(key)
        logger.info(f"{key}: {value if 'SECRET' not in key else '***'}")
    logger.info("-" * 40)
    
    # Try to read the .env file directly
    try:
        with open(dotenv_path, 'r', encoding='utf-8') as f:
            logger.info("\n.env file contents:")
            logger.info("-" * 40)
            for line in f:
                # Hide sensitive data
                if 'SECRET' in line:
                    logger.info("TOS_API_SECRET=***")
                else:
                    logger.info(line.strip())
            logger.info("-" * 40)
    except Exception as e:
        logger.error(f"Error reading .env file: {e}")
    
    client = ThinkOrSwimClient()
    
    # Test basic quote
    logger.info("\nTesting single quote...")
    quote = client.get_quote('AAPL')
    if quote:
        logger.info(f"AAPL Quote: ${quote.get('lastPrice', 'N/A')}")
    
    # Test multiple quotes
    logger.info("\nTesting multiple quotes...")
    quotes = client.get_multiple_quotes(['SPY', 'QQQ', 'DIA'])
    if quotes:
        for symbol, data in quotes.items():
            logger.info(f"{symbol} Quote: ${data.get('lastPrice', 'N/A')}")
    
    # Test market hours
    logger.info("\nTesting market hours...")
    hours = client.get_market_hours(['EQUITY'])
    if hours:
        is_open = hours.get('equity', {}).get('EQ', {}).get('isOpen', False)
        logger.info(f"Market is {'open' if is_open else 'closed'}")
    
    # Test market movers
    logger.info("\nTesting market movers...")
    movers = client.get_movers('$SPX.X')
    if movers:
        logger.info("Top SPX Movers:")
        for mover in movers[:3]:  # Show top 3
            logger.info(f"{mover.get('symbol')}: {mover.get('description')} ({mover.get('change')}%)")

if __name__ == '__main__':
    test_market_data()
