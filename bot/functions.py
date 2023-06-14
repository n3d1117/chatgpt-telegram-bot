import json

from plugins.weather import weather_function_spec, get_current_weather


def get_functions_specs():
    """
    Return the list of function specs that can be called by the model
    """
    return [
        weather_function_spec(),
    ]


async def call_function(function_name, arguments):
    """
    Call a function based on the name and parameters provided
    """
    if function_name == "get_current_weather":
        arguments = json.loads(arguments)
        return await get_current_weather(arguments["latitude"], arguments["longitude"], arguments["unit"])

    raise Exception(f"Function {function_name} not found")
