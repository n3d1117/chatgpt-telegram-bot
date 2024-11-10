import os
from typing import Dict

import requests

from .plugin import Plugin


# Author: https://github.com/zchk0
class CoinMarketCap(Plugin):
    """
    A plugin to fetch the current rate of various cryptocurrencies
    """
    def get_source_name(self) -> str:
        return "CoinMarketCap by zchk0"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "get_crypto_rate",
            "description": "Get the current rate of various cryptocurrencies from coinmarketcap",
            "parameters": {
                "type": "object",
                "properties": {
                    "asset": {"type": "string", "description": "Asset of the crypto"}
                },
                "required": ["asset"],
            },
        }]

    def get_crypto_price(self, asset):
        headers = {
            'X-CMC_PRO_API_KEY': os.environ.get('COINMARKETCAP_KEY', '')
        }
        params = {
            'symbol': asset,
            'convert': 'USD'
        }
        try:
            response = requests.get("https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest", headers=headers, params=params)
            response.raise_for_status()
            data = response.json().get('data', {})
            if asset in data:
                price = data[asset]['quote']['USD']['price']
                return price
            else:
                return "Not found"
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return None

    async def execute(self, function_name, helper, **kwargs) -> dict:
        asset = kwargs.get('asset', '')
        rate = self.get_crypto_price(asset)
        return {"asset": asset, "rate": rate}
