import os
import tweepy
import logging
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwitterClient:
    def __init__(self):
        """Initialize Twitter client"""
        load_dotenv()
        self.client = self._create_client()
        self.rate_limit_reset = 0
        self.remaining_requests = None
        self.last_request_time = 0
        self.request_interval = 20  # Fixed 20 seconds between requests

    def _create_client(self):
        """Create a new Twitter API v2 client"""
        try:
            bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
            if not bearer_token:
                logger.error("Twitter Bearer Token not found")
                return None
                
            return tweepy.Client(
                bearer_token=bearer_token,
                wait_on_rate_limit=True,
                return_type=dict
            )
        except Exception as e:
            logger.error(f"Failed to create Twitter client: {e}")
            return None

    def _wait_for_rate_limit(self):
        """Ensure we wait 20 seconds between requests"""
        now = time.time()
        if self.last_request_time > 0:
            time_since_last = now - self.last_request_time
            if time_since_last < self.request_interval:
                wait_time = self.request_interval - time_since_last
                logger.info(f"Waiting {wait_time:.1f} seconds before next request...")
                time.sleep(wait_time)
        self.last_request_time = time.time()

    def _handle_rate_limit(self, response):
        """Handle rate limit information from response"""
        if hasattr(response, 'headers'):
            self.remaining_requests = int(response.headers.get('x-rate-limit-remaining', 0))
            reset_time = int(response.headers.get('x-rate-limit-reset', 0))
            self.rate_limit_reset = datetime.fromtimestamp(reset_time)
            
            logger.info(f"Remaining API requests: {self.remaining_requests}")
            
            if self.remaining_requests == 0:
                wait_time = (self.rate_limit_reset - datetime.now()).total_seconds()
                if wait_time > 0:
                    logger.warning(f"Rate limit reached. Reset in {wait_time:.0f} seconds")
                    raise Exception(f"Rate limit exceeded. Please wait {wait_time:.0f} seconds.")

    def get_tweets(self, keywords, hours_lookback=1, max_tweets=100):
        """Get recent tweets for given keywords"""
        if not self.client:
            logger.error("Twitter client not initialized")
            return []

        tweets = []
        start_time = datetime.utcnow() - timedelta(hours=hours_lookback)

        for keyword in keywords:
            try:
                # Wait 20 seconds before making request
                self._wait_for_rate_limit()
                
                logger.info(f"Searching tweets for {keyword}")
                query = f"{keyword} -is:retweet lang:en"
                
                # Make request with reduced max_results
                response = self.client.search_recent_tweets(
                    query=query,
                    max_results=min(max_tweets, 10),  # Reduced max results per request
                    start_time=start_time,
                    tweet_fields=['created_at', 'public_metrics']
                )
                
                # Handle rate limits
                self._handle_rate_limit(response)
                
                if response and 'data' in response:
                    new_tweets = len(response['data'])
                    tweets.extend(response['data'])
                    logger.info(f"Found {new_tweets} tweet{'s' if new_tweets != 1 else ''} for {keyword}")
                else:
                    logger.warning(f"No tweets found for {keyword}")

            except Exception as e:
                if "Rate limit" in str(e):
                    raise  # Re-raise rate limit exceptions
                logger.error(f"Error searching tweets for {keyword}: {e}")
                continue

        return tweets
