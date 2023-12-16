import datetime
import tempfile
from typing import Dict

from .plugin import Plugin


class AutoTextToSpeech(Plugin):
    """
    A plugin to convert text to speech using Openai Speech API
    """

    def get_source_name(self) -> str:
        return "TTS"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "translate_text_to_speech",
            "description": "Translate text to speech using OpenAI API",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to translate to speech"},
                },
                "required": ["text"],
            },
        }]

    async def execute(self, function_name, helper, **kwargs) -> Dict:
        try:
            bytes, text_length = await helper.generate_speech(text=kwargs['text'])
            with tempfile.NamedTemporaryFile(delete=False, suffix='.opus') as temp_file:
                temp_file.write(bytes.getvalue())
                temp_file_path = temp_file.name
        except Exception as e:
            logging.exception(e)
            return {"Result": "Exception: " + str(e)}
        return {
            'direct_result': {
                'kind': 'file',
                'format': 'path',
                'value': temp_file_path
            }
        }
