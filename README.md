# Automated Trading Bot

This trading bot integrates Alpaca Markets API and OpenAI to make automated trading decisions based on market data and technical analysis.

## Features
- Alpaca Markets API integration for:
  - Real-time market data
  - Trade execution
  - Portfolio management
  - Technical indicators
- OpenAI API for advanced market analysis and decision making
- Real-time dashboard for monitoring:
  - Portfolio performance
  - Open positions
  - Recent trades
  - Market indicators
- Automated trading strategies based on technical analysis

## Setup Instructions

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your API credentials:
```
# Alpaca API
ALPACA_API_KEY=your_api_key
ALPACA_API_SECRET=your_api_secret
ALPACA_PAPER_TRADING=true  # Set to false for live trading

# OpenAI API
OPENAI_API_KEY=your_api_key

# Flask
FLASK_SECRET_KEY=your_secret_key
```

3. Configure your trading parameters in `config.py`

4. Run the web application:
```bash
python web_app.py
```

## Dashboard
The trading bot includes a web-based dashboard that provides:
- Real-time portfolio value and performance metrics
- Current positions and their P&L
- Recent trade history
- Market data and technical indicators
- Trading bot status and controls

Access the dashboard at `http://localhost:5000` after starting the web application.

## Trading Strategies
The bot implements technical analysis-based trading strategies using:
- RSI (Relative Strength Index)
- Moving Averages
- Volume Analysis
- Market Breadth Indicators

Strategy parameters can be configured in `config.py`.

## Security Notice
- Never commit your `.env` file or expose your API keys
- Use paper trading for testing (enabled by default)
- Monitor the bot's activities regularly
- Set appropriate position sizes and risk limits in `config.py`

## Deployment
The project uses automated deployment via GitHub webhooks. When changes are pushed to the main branch, they are automatically deployed to the production server.

### Manual Deployment
If needed, manual deployment can be performed using:
```bash
./deploy.sh
```

This script will:
1. Pull the latest changes from GitHub
2. Install any new dependencies
3. Restart the necessary services

## Disclaimer
This bot is for educational purposes. Trade at your own risk. Always test thoroughly with paper trading before using real money. Past performance does not guarantee future results.
