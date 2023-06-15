import json

import requests

from plugins.hookspec import hook_impl


class WeatherPlugin:
    @hook_impl
    def get_spec(self):
        return {
            "name": "get_current_weather",
            "description": "Get the current and 7-day daily weather forecast for a location using Open Meteo APIs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "string",
                        "description": "Latitude of the location",
                    },
                    "longitude": {
                        "type": "string",
                        "description": "Longitude of the location",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The temperature unit to use. Infer this from the provided location.",
                    },
                },
                "required": ["latitude", "longitude", "unit"],
            },
        }

    @hook_impl
    async def run(self, arguments):
        arguments = json.loads(arguments)
        latitude = arguments["latitude"]
        longitude = arguments["longitude"]
        unit = arguments["unit"]
        request = requests.get(
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}"
            f"&longitude={longitude}"
            f"&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_mean,"
            f"&forecast_days=7"
            f"&timezone=auto"
            f"&temperature_unit={unit}"
            f"&current_weather=true"
        )
        return json.dumps(request.json())
