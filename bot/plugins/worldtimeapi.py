import os
from typing import Dict
from WorldTimeAPI import service as serv

from .plugin import Plugin

class WorldTimeApiPlugin(Plugin):
    """
    A plugin to get the current time from a given timezone, using WorldTimeAPI
    """

    def __init__(self):
        wta_timezone = os.getenv('WORLDTIME_DEFAULT_TIMEZONE')
        if not wta_timezone:
            raise ValueError('WORLDTIME_DEFAULT_TIMEZONE environment variable must be set to use WorldTimeApiPlugin')
        self.plugin_tz = wta_timezone

    def get_source_name(self) -> str:
        return "WorldTimeAPI"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "worldtimeapi",
            "description": "Get the current time from a given timezone. use " + self.plugin_tz + " if not specified. include 12hr format in the response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "area": {
                        "type": "string",
                        "description": "the continent or region of the location"
                    },
                    "location": {
                        "type": "string",
                        "description": "the city"
                    }
                },
                "required": ["area", "location"],
            },
        }]

    async def execute(self, function_name, **kwargs) -> Dict:
        wtime = serv.Client('timezone')
        
        requests = {
            "area": kwargs['area'], 
            "location": kwargs['location']
        }

        response = wtime.get(**requests)
        
        try:
            res = response.datetime
        except:
            res = {"result": "No WorldTimeAPI result was found"}
        
        return res
