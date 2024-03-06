import logging
from typing import Dict

import requests

from .plugin import Plugin


# Author: https://github.com/stumpyfr
class CryptoPlugin(Plugin):
    """
    A plugin to fetch the current rate of various cryptocurrencies
    """
    def get_source_name(self) -> str:
        return "CoinCap"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "get_crypto_rate",
            "description": "Get the current rate of various crypto currencies",
            "parameters": {
                "type": "object",
                "properties": {
                    "asset": {"type": "string", "description": "Asset of the crypto"}
                },
                "required": ["asset"],
            },
        }]

    async def execute(self, function_name, helper, **kwargs) -> Dict:
        if kwargs["asset"] == "btc" or kwargs["asset"] == "BTC":
            kwargs["asset"] = "bitcoin"
        logging.info(f"crypto plugin works, the asset is: {kwargs}")
        response = requests.get(f"https://api.coincap.io/v2/assets/{kwargs['asset']}").json()
        logging.info(f"the coin price {response}")
        return response
