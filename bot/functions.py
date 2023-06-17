import json

from plugins.crypto import CryptoPlugin
from plugins.weather import WeatherPlugin
from plugins.web_search import WebSearchPlugin
from plugins.wolfram_alpha import WolframAlphaPlugin


class PluginManager:
    """
    A class to manage the plugins and call the correct functions
    """
    def __init__(self, config):
        enabled_plugins = config.get('plugins', [])
        plugins = [
            WolframAlphaPlugin() if 'wolfram' in enabled_plugins else None,
            WeatherPlugin() if 'weather' in enabled_plugins else None,
            CryptoPlugin() if 'crypto' in enabled_plugins else None,
            WebSearchPlugin() if 'web_search' in enabled_plugins else None,
        ]
        self.plugins = [plugin for plugin in plugins if plugin is not None]

    def get_functions_specs(self):
        """
        Return the list of function specs that can be called by the model
        """
        return [plugin.get_spec() for plugin in self.plugins]

    async def call_function(self, function_name, arguments):
        """
        Call a function based on the name and parameters provided
        """
        plugin = self.__get_plugin_by_function_name(function_name)
        if not plugin:
            return json.dumps({'error': f'Function {function_name} not found'})
        return json.dumps(await plugin.execute(**json.loads(arguments)))

    def get_plugin_source_name(self, function_name) -> str:
        """
        Return the source name of the plugin
        """
        plugin = self.__get_plugin_by_function_name(function_name)
        if not plugin:
            return ''
        return plugin.get_source_name()

    def __get_plugin_by_function_name(self, function_name):
        return next((plugin for plugin in self.plugins if plugin.get_spec().get('name') == function_name), None)
