# Automated Trading Bot

This trading bot integrates ThinkOrSwim (TOS), Twitter, and OpenAI to make automated trading decisions based on market data and sentiment analysis.

## Features
- ThinkorSwim API integration for market data and trade execution
- Twitter API integration for real-time market sentiment analysis
- OpenAI API for advanced text analysis and decision making
- Automated trading strategy execution

## Setup Instructions

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your API credentials:
```
# ThinkorSwim API
TOS_API_KEY=your_api_key
TOS_REDIRECT_URI=your_redirect_uri
TOS_ACCOUNT_ID=your_account_id

# Twitter API
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret

# OpenAI API
OPENAI_API_KEY=your_api_key
```

3. Configure your trading parameters in `config.py`

4. Run the bot:
```bash
python main.py
```

## Security Notice
- Never commit your `.env` file or expose your API keys
- Use paper trading for testing
- Monitor the bot's activities regularly
- Set appropriate trading limits

## Disclaimer
This bot is for educational purposes. Trade at your own risk. Always test thoroughly with paper trading before using real money.
