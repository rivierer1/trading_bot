import os
from openai import OpenAI
from dotenv import load_dotenv

class AIAnalyzer:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def analyze_sentiment(self, texts):
        if not texts:
            return 0
        
        # Reload environment variables and reinitialize client
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Combine texts for batch analysis
        combined_text = "\n".join(texts[:5])  # Analyze up to 5 tweets at once
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial sentiment analyzer. Respond only with a number between -1 and 1."},
                    {"role": "user", "content": f"Analyze the following market-related texts and determine the overall sentiment on a scale from -1 (very negative) to 1 (very positive). Consider market implications:\n\n{combined_text}\n\nReturn only the numerical score."}
                ]
            )
            
            sentiment_score = float(response.choices[0].message.content.strip())
            return max(min(sentiment_score, 1), -1)  # Ensure the score is between -1 and 1
        except Exception as e:
            print(f"Error in sentiment analysis: {str(e)}")
            return 0

    def analyze_market_context(self, market_data, tweets):
        if not tweets:
            return "No tweets available for analysis."
            
        # Reload environment variables and reinitialize client
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Combine tweets for analysis
        tweet_text = "\n".join([tweet.text for tweet in tweets[:3]])
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial market analyst."},
                    {"role": "user", "content": f"Analyze the following market data and social media sentiment to provide trading insights:\n\nMarket Data Summary:\n{market_data}\n\nRecent Social Media Sentiment:\n{tweet_text}\n\nProvide a brief analysis of market conditions and potential trading opportunities."}
                ]
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error in market context analysis: {str(e)}")
            return "Error analyzing market context."
