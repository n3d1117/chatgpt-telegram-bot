import json

import requests


def weather_function_spec():
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


async def get_current_weather(latitude, longitude, unit):
    """
    Get the current weather in a given location using the Open Meteo API
    Source: https://open-meteo.com/en/docs
    :param latitude: The latitude of the location to get the weather for
    :param longitude: The longitude of the location to get the weather for
    :param unit: The unit to use for the temperature (`celsius` or `fahrenheit`)
    :return: The JSON response to be fed back to the model
    """
    request = requests.get(f'https://api.open-meteo.com/v1/forecast'
                           f'?latitude={latitude}'
                           f'&longitude={longitude}'
                           f'&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_mean,'
                           f'&forecast_days=7'
                           f'&timezone=auto'
                           f'&temperature_unit={unit}'
                           f'&current_weather=true')
    return json.dumps(request.json())
