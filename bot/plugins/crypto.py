import json

import requests

from plugins.hookspec import hook_impl


class CryptoPlugin:
    """Get the current rate of various crypto currencies"""

    @hook_impl
    def get_spec(self):
        return {
            "name": "get_crypto_rate",
            "description": "Get the current rate of various crypto currencies",
            "parameters": {
                "type": "object",
                "properties": {
                    "asset": {"type": "string", "description": "Asset of the crypto"}
                },
                "required": ["asset"],
            },
        }

    @hook_impl
    async def run(self, arguments):
        arguments = json.loads(arguments)
        asset = arguments["asset"]
        request = requests.get(f"https://api.coincap.io/v2/rates/{asset}")
        return json.dumps(request.json())
