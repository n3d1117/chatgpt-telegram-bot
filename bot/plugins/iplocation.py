import requests
from typing import Dict

from .plugin import Plugin


class IpLocationPlugin(Plugin):
    """
    A plugin to get geolocation and other information for a given IP address
    """

    def get_source_name(self) -> str:
        return "IP.FM"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "iplocation",
            "description": "Get information for an IP address using the IP.FM API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ip": {"type": "string", "description": "IP Address"}
                },
                "required": ["ip"],
            },
        }]
        
    async def execute(self, function_name, helper, **kwargs) -> Dict:
        ip = kwargs.get('ip')
        BASE_URL = "https://api.ip.fm/?ip={}"
        url = BASE_URL.format(ip)
        try:
            response = requests.get(url)
            response_data = response.json()
            country = response_data.get('data', {}).get('country', "None")
            subdivisions = response_data.get('data', {}).get('subdivisions', "None")
            city = response_data.get('data', {}).get('city', "None")
            location = ', '.join(filter(None, [country, subdivisions, city])) or "None"
        
            asn = response_data.get('data', {}).get('asn', "None")
            as_name = response_data.get('data', {}).get('as_name', "None")
            as_domain = response_data.get('data', {}).get('as_domain', "None")       
            return {"Location": location, "ASN": asn, "AS Name": as_name, "AS Domain": as_domain}
        except Exception as e:
            return {"Error": str(e)}
