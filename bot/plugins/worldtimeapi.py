import os, requests
from typing import Dict
from datetime import datetime

from .plugin import Plugin


class WorldTimeApiPlugin(Plugin):
    """
    A plugin to get the current time from a given timezone, using WorldTimeAPI
    """
    def __init__(self):
        default_timezone = os.getenv('WORLDTIME_DEFAULT_TIMEZONE')
        if not default_timezone:
            raise ValueError('WORLDTIME_DEFAULT_TIMEZONE environment variable must be set to use WorldTimeApiPlugin')
        self.default_timezone = default_timezone

    def get_source_name(self) -> str:
        return "WorldTimeAPI"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "worldtimeapi",
            "description": f"Get the current time from a given timezone",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": f"The timezone identifier (e.g: `Europe/Rome`). Infer this from the location."
                                       f"Use {self.default_timezone} if not specified."
                    }
                },
                "required": ["timezone"],
            },
        }]

    async def execute(self, function_name, **kwargs) -> Dict:
        timezone = kwargs.get('timezone', self.default_timezone)
        url = f'https://worldtimeapi.org/api/timezone/{timezone}'

        try:
            wtr = requests.get(url).json().get('datetime')
            wtr_obj = datetime.strptime(wtr, "%Y-%m-%dT%H:%M:%S.%f%z")
            time_24hr = wtr_obj.strftime("%H:%M:%S")
            time_12hr = wtr_obj.strftime("%I:%M:%S %p")
            return {"24hr": time_24hr, "12hr": time_12hr}
        except:
            return {"result": "No result was found"}
