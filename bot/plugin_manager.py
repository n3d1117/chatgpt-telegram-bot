import json

from plugins.images import ImageSearchPlugin
from plugins.translate import TranslatePlugin
from plugins.spotify import SpotifyPlugin
from plugins.crypto import CryptoPlugin
from plugins.weather import WeatherPlugin
from plugins.web_search import WebSearchPlugin
from plugins.wolfram_alpha import WolframAlphaPlugin
from plugins.worldtimeapi import WorldTimeApiPlugin

class PluginManager:
    """
    A class to manage the plugins and call the correct functions
    """
    def __init__(self, config):
        enabled_plugins = config.get('plugins', [])
        plugin_mapping = {
            'wolfram': WolframAlphaPlugin,
            'weather': WeatherPlugin,
            'crypto': CryptoPlugin,
            'web_search': WebSearchPlugin,
            'spotify': SpotifyPlugin,
            'translate': TranslatePlugin,
            'image_search': ImageSearchPlugin,
            'worldtimeapi': WorldTimeApiPlugin,
        }
        self.plugins = [plugin_mapping[plugin]() for plugin in enabled_plugins if plugin in plugin_mapping]

    def get_functions_specs(self):
        """
        Return the list of function specs that can be called by the model
        """
        return [spec for specs in map(lambda plugin: plugin.get_spec(), self.plugins) for spec in specs]

    async def call_function(self, function_name, arguments):
        """
        Call a function based on the name and parameters provided
        """
        plugin = self.__get_plugin_by_function_name(function_name)
        if not plugin:
            return json.dumps({'error': f'Function {function_name} not found'})
        return json.dumps(await plugin.execute(function_name, **json.loads(arguments)))

    def get_plugin_source_name(self, function_name) -> str:
        """
        Return the source name of the plugin
        """
        plugin = self.__get_plugin_by_function_name(function_name)
        if not plugin:
            return ''
        return plugin.get_source_name()

    def __get_plugin_by_function_name(self, function_name):
        return next((plugin for plugin in self.plugins
                     if function_name in map(lambda spec: spec.get('name'), plugin.get_spec())), None)
