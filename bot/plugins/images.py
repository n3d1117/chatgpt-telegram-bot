from itertools import islice
from typing import Dict

from duckduckgo_search import DDGS

from .plugin import Plugin


class ImageSearchPlugin(Plugin):
    """
    A plugin to search images and GIFs for a given query, using DuckDuckGo
    """
    def get_source_name(self) -> str:
        return "DuckDuckGo Images"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "search_images",
            "description": "Search image or GIFs for a given query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The query to search for"},
                    "type": {
                        "type": "string",
                        "enum": ["photo", "gif"],
                        "description": "The type of image to search for. Default to photo if not specified",
                    }
                },
                "required": ["query", "type"],
            },
        }]

    async def execute(self, function_name, **kwargs) -> Dict:
        with DDGS() as ddgs:
            ddgs_images_gen = ddgs.images(
                kwargs['query'],
                region="wt-wt",
                safesearch='off',
                type_image=kwargs['type'],
            )
            results = list(islice(ddgs_images_gen, 1))
            return {"result": results[0]["image"]}
