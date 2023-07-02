import os
from typing import Dict

import requests

from .plugin import Plugin


class DeeplTranslatePlugin(Plugin):
    """
    A plugin to translate a given text from a language to another, using DeepL
    """

    def __init__(self):
            deepl_api_key = os.getenv('DEEPL_API_KEY')
            if not deepl_api_key:
                raise ValueError('DEEPL_API_KEY environment variable must be set to use DeeplPlugin')
            self.api_key = deepl_api_key

    def get_source_name(self) -> str:
        return "DeepL Translate"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "translate",
            "description": "Translate a given text from a language to another",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to translate"},
                    "to_language": {"type": "string", "description": "The language to translate to (e.g. 'it')"}
                },
                "required": ["text", "to_language"],
            },
        }]

    async def execute(self, function_name, **kwargs) -> Dict:
        translator = requests.get(
            "https://api.deepl.com/v2/translate",
            params={ 
                "auth_key": self.api_key, 
                "target_lang": kwargs['to_language'], 
                "text": kwargs['text'], 
            }, 
        ) 
        translated_text = translator.json()["translations"][0]["text"]
        return translated_text
