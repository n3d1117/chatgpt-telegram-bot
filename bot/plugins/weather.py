from typing import Dict

import requests

from bot.plugins.plugin import Plugin


class WeatherPlugin(Plugin):
    """
    A plugin to get the current weather and 7-day daily forecast for a location
    """
    def get_source_name(self) -> str:
        return "OpenMeteo"

    def get_spec(self) -> Dict:
        return {
            "name": "get_current_weather",
            "description": "Get the current and 7-day daily weather forecast for a location using Open Meteo APIs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "string",
                        "description": "Latitude of the location"
                    },
                    "longitude": {
                        "type": "string",
                        "description": "Longitude of the location"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The temperature unit to use. Infer this from the provided location.",
                    },
                },
                "required": ["latitude", "longitude", "unit"],
            }
        }

    async def execute(self, **kwargs) -> Dict:
        url = f'https://api.open-meteo.com/v1/forecast'\
              f'?latitude={kwargs["latitude"]}'\
              f'&longitude={kwargs["longitude"]}'\
              f'&temperature_unit={kwargs["unit"]}' \
              '&current_weather=true' \
              '&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_mean,' \
              '&forecast_days=7' \
              '&timezone=auto'
        return requests.get(url).json()
