import os
import logging
from datetime import datetime, timedelta
import pandas as pd
from tda import auth, client
from selenium import webdriver
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThinkOrSwimClient:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('TOS_API_KEY')
        if not self.api_key:
            logger.error("TOS_API_KEY not found in environment variables")
        else:
            logger.info(f"Loaded API key: {self.api_key[:5]}...")  # Only log first 5 chars for security
            
        self.api_secret = os.getenv('TOS_API_SECRET')
        self.redirect_uri = os.getenv('TOS_REDIRECT_URI', 'http://localhost:8080')
        self.token_path = 'token.json'
        self.account_id = int(os.getenv('TOS_ACCOUNT_ID')) if os.getenv('TOS_ACCOUNT_ID') else None
        self.client = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with TD Ameritrade API"""
        try:
            if not self.api_key:
                logger.error("TOS_API_KEY not found in environment variables")
                return

            if os.path.exists(self.token_path):
                logger.info("Found existing token file, attempting to use it...")
                try:
                    self.client = auth.client_from_token_file(
                        self.token_path,
                        self.api_key
                    )
                    logger.info("Successfully authenticated with token file")
                    return
                except Exception as e:
                    logger.warning(f"Failed to authenticate with token file: {e}")
                    # Token might be expired, try webdriver auth
            
            logger.info("Starting webdriver authentication...")
            try:
                # For Chrome
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.options import Options

                chrome_options = Options()
                # chrome_options.add_argument("--headless")  # Run in headless mode
                chrome_options.add_argument("--ignore-certificate-errors")  # Accept self-signed certificates
                chrome_options.add_argument("--ignore-ssl-errors")
                chrome_options.add_argument("--allow-insecure-localhost")
                
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                
                self.client = auth.client_from_login_flow(
                    driver,
                    self.api_key,
                    self.redirect_uri,
                    self.token_path
                )
                logger.info("Successfully authenticated with webdriver")
                driver.quit()
            except Exception as e:
                logger.error(f"Webdriver authentication failed: {e}")
                if 'driver' in locals():
                    driver.quit()
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")

    def _ensure_authenticated(self):
        """Ensure we have an authenticated client"""
        if not self.client:
            logger.warning("Client not authenticated, attempting to authenticate...")
            self._authenticate()
        return self.client is not None

    def get_quote(self, symbol):
        """Get real-time quote for a symbol"""
        if not self._ensure_authenticated():
            return None
        try:
            response = self.client.get_quote(symbol)
            quote_data = response.json()
            if symbol in quote_data:
                logger.info(f"Successfully retrieved quote for {symbol}")
                return quote_data[symbol]
            logger.warning(f"No quote data found for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {str(e)}")
            return None

    def get_multiple_quotes(self, symbols):
        """Get real-time quotes for multiple symbols"""
        if not self._ensure_authenticated():
            return None
        try:
            response = self.client.get_quotes(symbols)
            quote_data = response.json()
            logger.info(f"Successfully retrieved quotes for {len(quote_data)} symbols")
            return quote_data
        except Exception as e:
            logger.error(f"Error getting multiple quotes: {str(e)}")
            return None

    def get_price_history(self, symbol, period_type='day', period=5,
                         frequency_type='minute', frequency=1):
        """Get historical price data with specified parameters"""
        if not self._ensure_authenticated():
            return None
        try:
            response = self.client.get_price_history(
                symbol,
                period_type=period_type,
                period=period,
                frequency_type=frequency_type,
                frequency=frequency
            )
            data = response.json()
            if 'candles' in data:
                df = pd.DataFrame(data['candles'])
                df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
                df.set_index('datetime', inplace=True)
                logger.info(f"Retrieved {len(df)} price points for {symbol}")
                return df
            logger.warning(f"No price history data found for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Error getting price history for {symbol}: {str(e)}")
            return None

    def get_intraday_data(self, symbol, days_back=1):
        """Get minute-by-minute data for the last N days"""
        if not self._ensure_authenticated():
            return None
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            response = self.client.get_price_history_every_minute(
                symbol,
                start_datetime=start_date,
                end_datetime=end_date
            )
            data = response.json()
            
            if 'candles' in data:
                df = pd.DataFrame(data['candles'])
                df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
                df.set_index('datetime', inplace=True)
                logger.info(f"Retrieved {len(df)} minute bars for {symbol}")
                return df
            logger.warning(f"No intraday data found for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Error getting intraday data for {symbol}: {str(e)}")
            return None

    def get_market_hours(self, markets=['EQUITY']):
        """Get market hours for specified markets"""
        if not self._ensure_authenticated():
            return None
        try:
            response = self.client.get_market_hours(markets=markets)
            hours_data = response.json()
            logger.info(f"Retrieved market hours for {len(markets)} markets")
            return hours_data
        except Exception as e:
            logger.error(f"Error getting market hours: {str(e)}")
            return None

    def get_movers(self, index, direction='up', change='percent'):
        """Get market movers for an index (e.g., $SPX.X, $DJI, $COMPX)"""
        if not self._ensure_authenticated():
            return None
        try:
            response = self.client.get_movers(
                index,
                direction=direction,  # 'up' or 'down'
                change=change  # 'value' or 'percent'
            )
            movers_data = response.json()
            logger.info(f"Retrieved {len(movers_data)} movers for {index}")
            return movers_data
        except Exception as e:
            logger.error(f"Error getting movers for {index}: {str(e)}")
            return None

    def get_option_chain(self, symbol):
        """Get option chain for a symbol"""
        if not self._ensure_authenticated():
            return None
        try:
            response = self.client.get_option_chain(symbol)
            chain_data = response.json()
            logger.info(f"Retrieved option chain for {symbol}")
            return chain_data
        except Exception as e:
            logger.error(f"Error getting option chain for {symbol}: {str(e)}")
            return None
