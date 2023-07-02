from typing import Dict

from duckduckgo_search import DDGS

from .plugin import Plugin


class DDGTranslatePlugin(Plugin):
    """
    A plugin to translate a given text from a language to another, using DuckDuckGo
    """
    def get_source_name(self) -> str:
        return "DuckDuckGo Translate"

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
        with DDGS() as ddgs:
            return ddgs.translate(kwargs['text'], to=kwargs['to_language'])
