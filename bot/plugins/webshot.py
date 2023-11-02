import os, requests, random, string
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
            "description": "Show screenshot/image of a website from a given url or domain name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Website url or domain name. Correctly formatted url is required. Example: https://www.google.com"}
                },
                "required": ["url"],
            },
        }]
    
    def generate_random_string(self, length):
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    async def execute(self, function_name, **kwargs) -> Dict:
        try:
            image_url = f'https://image.thum.io/get/maxAge/12/width/720/{kwargs["url"]}'
            
            # preload url first
            requests.get(image_url)

            # download the actual image
            response = requests.get(image_url, timeout=30)

            if response.status_code == 200:
                if not os.path.exists("uploads/webshot"):
                    os.makedirs("uploads/webshot")

                image_file_path = os.path.join("uploads/webshot", f"{self.generate_random_string(15)}.png")
                with open(image_file_path, "wb") as f:
                    f.write(response.content)

                return {
                    'direct_result': {
                        'kind': 'photo',
                        'format': 'path',
                        'value': image_file_path
                    }
                }
            else:
                return {'result': 'Unable to screenshot website'}
        except:
            if 'image_file_path' in locals():
                os.remove(image_file_path)
                
            return {'result': 'Unable to screenshot website'}
