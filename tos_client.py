import os
import logging
from datetime import datetime, timedelta
import pandas as pd
from tda import auth, client
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
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
            # Ensure API key has the correct suffix
            if not self.api_key.endswith('@AMER.OAUTHAP'):
                self.api_key = f"{self.api_key}@AMER.OAUTHAP"
            logger.info(f"Using API key: {self.api_key[:5]}...@AMER.OAUTHAP")
            
        self.redirect_uri = 'http://localhost:8080'
        self.token_path = 'token.json'
        self.account_id = int(os.getenv('TOS_ACCOUNT_ID')) if os.getenv('TOS_ACCOUNT_ID') else None
        self.client = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with TD Ameritrade API (now through Schwab)"""
        try:
            if not self.api_key:
                raise ValueError("API key not found")

            logger.info("Starting TD Ameritrade authentication process...")
            logger.info(f"Using redirect URI: {self.redirect_uri}")
            
            # Try to authenticate using existing token
            try:
                logger.info("Attempting to use existing token...")
                self.client = auth.client_from_token_file(
                    self.token_path,
                    self.api_key
                )
                logger.info("Successfully authenticated using existing token")
                return
            except FileNotFoundError:
                logger.info("No token file found, starting new authentication flow")
            except Exception as e:
                logger.warning(f"Error using existing token: {e}")
                logger.info("Starting fresh authentication flow")
                
            # Configure Chrome options for Schwab login page
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager.chrome import ChromeDriverManager
            
            chrome_options = Options()
            chrome_options.add_argument('--start-maximized')  # Make window visible
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # These options help keep the browser open
            chrome_options.add_experimental_option("detach", True)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Create service with latest chromedriver
            service = Service(ChromeDriverManager().install())
            
            logger.info("Launching Chrome for authentication...")
            logger.info("Please complete the login process in the browser window")
            logger.info("Note: You may be redirected to Schwab's login page - this is expected")
            logger.info("DO NOT CLOSE THE BROWSER until authentication is complete")
            
            # Start new authentication flow with longer timeout
            driver = webdriver.Chrome(service=service, options=chrome_options)
            try:
                self.client = auth.client_from_login_flow(
                    driver,
                    self.api_key,
                    self.redirect_uri,
                    self.token_path,
                    redirect_wait_time_seconds=180  # Even longer timeout
                )
                logger.info("Authentication successful!")
                logger.info(f"Token saved to: {self.token_path}")
            except Exception as e:
                logger.error(f"Authentication failed: {e}")
                logger.error("If you're seeing Schwab's login page, this is expected due to the TD Ameritrade acquisition")
                logger.error("Please ensure you're using your TD Ameritrade credentials on the Schwab login page")
                self.client = None
            finally:
                try:
                    driver.quit()
                except:
                    pass
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            logger.error("If you're seeing Schwab's login page, this is expected due to the TD Ameritrade acquisition")
            logger.error("Please ensure you're using your TD Ameritrade credentials on the Schwab login page")
            self.client = None

    def _ensure_authenticated(self):
        """Ensure we have an authenticated client"""
        if not self.client:
            logger.error("No authenticated client available")
            raise Exception("Authentication required. Please run authentication process first.")
            
        # TODO: Add token refresh logic here if needed

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

    def test_connection(self):
        """Test TD Ameritrade API connection and permissions"""
        try:
            if not self.client:
                logger.error("No TD Ameritrade client available - check authentication")
                return False
            
            # Try to get all accounts first
            logger.info("Attempting to retrieve account information...")
            accounts = self.get_accounts()
            if accounts:
                logger.info(f"Successfully retrieved {len(accounts)} account(s)")
                for acc in accounts:
                    logger.info(f"Account found - ID: {acc['securitiesAccount']['accountId']}")
                return True
            else:
                logger.error("Failed to retrieve account information")
                return False
                
        except Exception as e:
            logger.error(f"TD Ameritrade API connection failed: {e}")
            if "401" in str(e):
                logger.error("Authentication failed - token may have expired")
            elif "403" in str(e):
                logger.error("Permission denied - check account permissions")
            elif "429" in str(e):
                logger.error("Rate limit exceeded - wait before trying again")
            return False

    def get_accounts(self):
        """Get all TD Ameritrade accounts associated with the authenticated user"""
        try:
            self._ensure_authenticated()
            response = self.client.get_accounts()
            
            if response.status_code == 200:
                accounts = response.json()
                logger.info("Successfully retrieved account information")
                return accounts
            else:
                logger.error(f"Failed to get accounts. Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting accounts: {str(e)}")
            return None

    def get_account_details(self, account_id=None):
        """Get detailed information for a specific account"""
        try:
            self._ensure_authenticated()
            account_id = account_id or self.account_id
            
            if not account_id:
                logger.error("No account ID provided")
                return None
                
            response = self.client.get_account(account_id)
            
            if response.status_code == 200:
                account = response.json()
                logger.info(f"Successfully retrieved details for account {account_id}")
                return account
            else:
                logger.error(f"Failed to get account details. Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting account details: {str(e)}")
            return None
