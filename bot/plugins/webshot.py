from typing import Dict
from .plugin import Plugin

class WebshotPlugin(Plugin):
    """
    A plugin to screenshot a website
    """
    def get_source_name(self) -> str:
        return "WebShot"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "screenshot_website",
            "description": "Show screenshot/image of a website from a given url or domain name",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Website url or domain name"}
                },
                "required": ["url"],
            },
        }]

    async def execute(self, function_name, **kwargs) -> Dict:
        return {
            'direct_result': {
                'kind': 'photo',
                'format': 'url',
                'value': f'https://image.thum.io/get/maxAge/12/width/720/{kwargs["url"]}'
            }
        }
