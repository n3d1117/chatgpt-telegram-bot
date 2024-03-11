import asyncio
import datetime
import tempfile
import traceback
from typing import Dict
import telegram

from .plugin import Plugin


class AutoDalle(Plugin):
    """
    A plugin to generate image using Openai image generation API
    """

    def get_source_name(self) -> str:
        return "DALLE"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "dalle_image",
            "description": "Create image from scratch based on a text prompt (DALL·E 3 and DALL·E 2). Send to user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "prompt": "Image description. Use English language for better results."},
                },
                "required": ["prompt"],
            },
        }]

    async def execute(self, function_name, bot, tg_upd: telegram.Update, chat_id, **kwargs) -> Dict:
        await bot.wrap_with_indicator(tg_upd, bot.image_gen(tg_upd, kwargs['prompt']), "upload_photo")
        return {
            'direct_result': {
                'kind': 'none',
                'format': '',
                'value': 'none',
            }
        }