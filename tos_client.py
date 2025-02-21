import os
from tda import auth, client
import json
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

class ThinkOrSwimClient:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('TOS_API_KEY')
        self.redirect_uri = os.getenv('TOS_REDIRECT_URI')
        self.token_path = 'token.json'
        self.account_id = os.getenv('TOS_ACCOUNT_ID')
        self.client = self._authenticate()

    def _authenticate(self):
        try:
            c = auth.client_from_token_file(self.token_path, self.api_key)
        except FileNotFoundError:
            from selenium import webdriver
            with webdriver.Chrome() as driver:
                c = auth.client_from_login_flow(
                    driver, self.api_key, self.redirect_uri, self.token_path)
        return c

    def get_quote(self, symbol):
        response = self.client.get_quote(symbol)
        return response.json()

    def place_order(self, symbol, quantity, order_type='MARKET', instruction='BUY'):
        order_spec = {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": "DAY",
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": instruction,
                    "quantity": quantity,
                    "instrument": {
                        "symbol": symbol,
                        "assetType": "EQUITY"
                    }
                }
            ]
        }
        return self.client.place_order(self.account_id, order_spec)

    def get_price_history(self, symbol, period_type='day', period=5,
                         frequency_type='minute', frequency=1):
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
            return df
        return None

    def get_account_positions(self):
        response = self.client.get_account(self.account_id, fields=client.Client.Account.Fields.POSITIONS)
        return response.json()
