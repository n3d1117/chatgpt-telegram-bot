from typing import Dict

from pytube import YouTube

from .plugin import Plugin


class YouTubeAudioExtractorPlugin(Plugin):
    """
    A plugin to extract audio from a YouTube video
    """

    def get_source_name(self) -> str:
        return "YouTube Audio Extractor"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "extract_youtube_audio",
            "description": "Extract audio from a YouTube video",
            "parameters": {
                "type": "object",
                "properties": {
                    "youtube_link": {"type": "string", "description": "YouTube video link to extract audio from"}
                },
                "required": ["youtube_link"],
            },
        }]

    async def execute(self, function_name, **kwargs) -> Dict:
        link = kwargs['youtube_link']
        try:
            video = YouTube(link)
            audio = video.streams.filter(only_audio=True, file_extension='mp4').first()
            output = video.title + '.mp4'
            audio.download(filename=output)
            return {
                'direct_result': {
                    'kind': 'file',
                    'format': 'path',
                    'value': output
                }
            }
        except:
            return {'result': 'Failed to extract audio'}
