import importlib
import pkgutil

import pluggy
from plugins.hookspec import PluggySpecs, HOOK_NAMESPACE
from plugins.crypto import CryptoPlugin
from plugins.weather import WeatherPlugin

plugin_manager = None

def get_functions_specs():
    """
    Return the list of function specs that can be called by the model
    """

    global plugin_manager
    if plugin_manager is None:
        plugin_manager = pluggy.PluginManager(HOOK_NAMESPACE)
        plugin_manager.add_hookspecs(PluggySpecs)
        # register here your plugins
        plugin_manager.register(WeatherPlugin())
        plugin_manager.register(CryptoPlugin())

    return plugin_manager.hook.get_spec()


async def call_function(function_name, arguments):
    """
    Call a function based on the name and parameters provided
    """

    global plugin_manager
    for plugin in plugin_manager.get_plugins():
        if plugin.get_spec()["name"] == function_name:
            return await plugin.run(arguments)

    raise Exception(f"Function {function_name} not found")
