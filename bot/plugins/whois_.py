from typing import Dict
from .plugin import Plugin

import whois


class WhoisPlugin(Plugin):
    """
    A plugin to query whois database
    """
    def get_source_name(self) -> str:
        return "Whois"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "get_whois",
            "description": "Get whois registration and expiry information for a domain",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain name"}
                },
                "required": ["domain"],
            },
        }]

    async def execute(self, function_name, helper, **kwargs) -> Dict:
        try:
            whois_result = whois.query(kwargs['domain'])
            if whois_result is None:
                return {'result': 'No such domain found'}
            return whois_result.__dict__
        except Exception as e:
            return {'error': 'An unexpected error occurred: ' + str(e)}
