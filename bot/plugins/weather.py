from datetime import datetime
from typing import Dict

import requests

from .plugin import Plugin


class WeatherPlugin(Plugin):
    """
    A plugin to get the current weather and 7-day daily forecast for a location
    """

    def get_source_name(self) -> str:
        return "OpenMeteo"

    def get_spec(self) -> [Dict]:
        latitude_param = {"type": "string", "description": "Latitude of the location"}
        longitude_param = {"type": "string", "description": "Longitude of the location"}
        unit_param = {
            "type": "string",
            "enum": ["celsius", "fahrenheit"],
            "description": "The temperature unit to use. Infer this from the provided location.",
        }
        return [
            {
                "name": "get_current_weather",
                "description": "Get the current weather for a location using Open Meteo APIs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "latitude": latitude_param,
                        "longitude": longitude_param,
                        "unit": unit_param,
                    },
                    "required": ["latitude", "longitude", "unit"],
                },
            },
            {
                "name": "get_forecast_weather",
                "description": "Get daily weather forecast for a location using Open Meteo APIs."
                               f"Today is {datetime.today().strftime('%A, %B %d, %Y')}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "latitude": latitude_param,
                        "longitude": longitude_param,
                        "unit": unit_param,
                        "forecast_days": {
                            "type": "integer",
                            "description": "The number of days to forecast, including today. Default is 7. Max 14. "
                                           "Use 1 for today, 2 for today and tomorrow, and so on.",
                        },
                    },
                    "required": ["latitude", "longitude", "unit", "forecast_days"],
                },
            }
        ]

    async def execute(self, function_name, helper, **kwargs) -> Dict:
        url = f'https://api.open-meteo.com/v1/forecast' \
              f'?latitude={kwargs["latitude"]}' \
              f'&longitude={kwargs["longitude"]}' \
              f'&temperature_unit={kwargs["unit"]}'
        if function_name == 'get_current_weather':
            url += '&current_weather=true'
            return requests.get(url).json()

        elif function_name == 'get_forecast_weather':
            url += '&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_mean,'
            url += f'&forecast_days={kwargs["forecast_days"]}'
            url += '&timezone=auto'
            response = requests.get(url).json()
            results = {}
            for i, time in enumerate(response["daily"]["time"]):
                results[datetime.strptime(time, "%Y-%m-%d").strftime("%A, %B %d, %Y")] = {
                    "weathercode": response["daily"]["weathercode"][i],
                    "temperature_2m_max": response["daily"]["temperature_2m_max"][i],
                    "temperature_2m_min": response["daily"]["temperature_2m_min"][i],
                    "precipitation_probability_mean": response["daily"]["precipitation_probability_mean"][i]
                }
            return {"today": datetime.today().strftime("%A, %B %d, %Y"), "forecast": results}
