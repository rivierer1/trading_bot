import os
import tweepy
from datetime import datetime, timedelta
from dotenv import load_dotenv

class TwitterClient:
    def __init__(self):
        load_dotenv()

    def get_tweets(self, keywords, hours_lookback=1, max_tweets=100):
        # Reload environment variables
        load_dotenv()
        self.client = tweepy.Client(
            bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
            consumer_key=os.getenv('TWITTER_API_KEY'),
            consumer_secret=os.getenv('TWITTER_API_SECRET'),
            wait_on_rate_limit=True
        )
        
        tweets = []
        start_time = datetime.utcnow() - timedelta(hours=hours_lookback)
        
        for keyword in keywords:
            query = f"{keyword} -is:retweet lang:en"
            try:
                response = self.client.search_recent_tweets(
                    query=query,
                    max_results=min(max_tweets, 100),  # API limit is 100
                    start_time=start_time,
                    tweet_fields=['created_at', 'public_metrics']
                )
                
                if response.data:
                    tweets.extend(response.data)
            except Exception as e:
                print(f"Error fetching tweets for {keyword}: {str(e)}")
        
        return tweets
