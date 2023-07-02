import os, requests
from typing import Dict
from datetime import datetime
from .plugin import Plugin

class WorldTimeApiPlugin(Plugin):
    """
    A plugin to get the current time from a given timezone, using WorldTimeAPI
    """

    def __init__(self):
        wta_timezone = os.getenv('WORLDTIME_DEFAULT_TIMEZONE')
        if not wta_timezone:
            raise ValueError('WORLDTIME_DEFAULT_TIMEZONE environment variable must be set to use WorldTimeApiPlugin')
        self.defTz = wta_timezone.split('/');

    def get_source_name(self) -> str:
        return "WorldTimeAPI"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "worldtimeapi",
            "description": f"Get the current time from a given timezone",
            "parameters": {
                "type": "object",
                "properties": {
                    "area": {
                        "type": "string",
                        "description": f"the continent of timezone identifier. use {self.defTz[0]} if not specified."
                    },
                    "location": {
                        "type": "string",
                        "description": f"the city/region of timezone identifier. use {self.defTz[1]} if not specified."
                    }
                },
                "required": ["area", "location"],
            },
        }]

    async def execute(self, function_name, **kwargs) -> Dict:
        areaVal = kwargs.get('area', self.defTz[0])
        locVal = kwargs.get('location', self.defTz[1])

        url = f'https://worldtimeapi.org/api/timezone/{areaVal}/{locVal}'
        
        try:
            wtr = requests.get(url).json().get('datetime')
            wtr_obj = datetime.strptime(wtr, "%Y-%m-%dT%H:%M:%S.%f%z")

            time_24hr = wtr_obj.strftime("%H:%M:%S")
            time_12hr = wtr_obj.strftime("%I:%M:%S %p")

            res = {
                "24hr": time_24hr,
                "12hr": time_12hr
            }
        except:
            res = {"result": "No WorldTimeAPI result was found"}
        
        return res
