import json

import requests
from geopy import Nominatim


def weather_function_spec():
    return {
        "name": "get_current_weather",
        "description": "Get the current and 7-day daily weather forecast for a location using Open Meteo APIs.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The exact city and state, e.g. San Francisco, CA"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "The temperature unit to use. Infer this from the provided location.",
                },
            },
            "required": ["location", "unit"],
        }
    }


async def get_current_weather(location, unit):
    """
    Get the current weather in a given location using the Open Meteo API
    Source: https://open-meteo.com/en/docs
    :param location: The location to get the weather for, in natural language
    :param unit: The unit to use for the temperature (`celsius` or `fahrenheit`)
    :return: The JSON response to be fed back to the model
    """
    geolocator = Nominatim(user_agent="chatgpt-telegram-bot")
    geoloc = geolocator.geocode(location)
    request = requests.get(f'https://api.open-meteo.com/v1/forecast'
                           f'?latitude={geoloc.latitude}'
                           f'&longitude={geoloc.longitude}'
                           f'&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_mean,'
                           f'&forecast_days=7'
                           f'&timezone=auto'
                           f'&temperature_unit={unit}'
                           f'&current_weather=true')
    return json.dumps(request.json())
