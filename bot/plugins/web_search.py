from itertools import islice
from typing import Dict

from duckduckgo_search import DDGS

from .plugin import Plugin


class WebSearchPlugin(Plugin):
    """
    A plugin to search the web for a given query, using DuckDuckGo
    """

    def get_source_name(self) -> str:
        return "DuckDuckGo"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "web_search",
            "description": "Execute a web search for the given query and return a list of results",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "the user query"
                    }
                },
                "required": ["query"],
            },
        }]

    async def execute(self, function_name, **kwargs) -> Dict:
        with DDGS() as ddgs:
            ddgs_gen = ddgs.text(
                kwargs['query'],
                region='wt-wt',
                safesearch='off'
            )
            results = list(islice(ddgs_gen, 8))

            if results is None or len(results) == 0:
                return {"Result": "No good DuckDuckGo Search Result was found"}

            def to_metadata(result: Dict) -> Dict[str, str]:
                return {
                    "snippet": result["body"],
                    "title": result["title"],
                    "link": result["href"],
                }
            return {"result": [to_metadata(result) for result in results]}
