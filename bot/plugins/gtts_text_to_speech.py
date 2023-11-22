import datetime
from typing import Dict

from gtts import gTTS

from .plugin import Plugin


class GTTSTextToSpeech(Plugin):
    """
    A plugin to convert text to speech using Google Translate's Text to Speech API
    """

    def get_source_name(self) -> str:
        return "gTTS"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "google_translate_text_to_speech",
            "description": "Translate text to speech using Google Translate's Text to Speech API",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to translate to speech"},
                    "lang": {
                        "type": "string", "description": "The language of the text to translate to speech."
                                                         "Infer this from the language of the text.",
                    },
                },
                "required": ["text", "lang"],
            },
        }]

    async def execute(self, function_name, **kwargs) -> Dict:
        tts = gTTS(kwargs['text'], lang=kwargs.get('lang', 'en'))
        output = f'gtts_{datetime.datetime.now().timestamp()}.mp3'
        tts.save(output)
        return {
            'direct_result': {
                'kind': 'file',
                'format': 'path',
                'value': output
            }
        }
