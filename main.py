from config import TradingConfig
from trading_bot import TradingBot
import logging

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('trading_bot.log'),
            logging.StreamHandler()
        ]
    )

def main():
    setup_logging()
    logging.info("Initializing trading bot...")
    
    # Create configuration
    config = TradingConfig()
    
    # Initialize and start the trading bot
    bot = TradingBot(config)
    
    try:
        bot.start()
    except KeyboardInterrupt:
        logging.info("Shutting down trading bot...")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    main()
