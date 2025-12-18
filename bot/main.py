import logging
import os

from dotenv import load_dotenv

from plugin_manager import PluginManager
from openai_helper import OpenAIHelper, default_max_tokens, are_functions_available
from telegram_bot import ChatGPTTelegramBot


def main():
    # Read .env file
    load_dotenv()

    def get_env(key, default=None, parser=None):
        value = os.environ.get(key, default)
        if parser:
            if value is not None:
                try:
                    return parser(value)
                except ValueError:
                    logging.warning(f"Invalid value for {key}: '{value}'. Using default: {default}")
                    return default
            else:
                return default
        return value

    def parse_float_list(value):
        if isinstance(value, list):
            return value
        return [float(i) for i in value.split(",")]



    # Setup logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Check if the required environment variables are set
    required_values = ['TELEGRAM_BOT_TOKEN', 'OPENAI_API_KEY']
    missing_values = [value for value in required_values if os.environ.get(value) is None]
    if len(missing_values) > 0:
        logging.error(f'The following environment values are missing in your .env: {", ".join(missing_values)}')
        exit(1)

    # Setup configurations
    model = get_env('OPENAI_MODEL', 'gpt-4o')
    functions_available = are_functions_available(model=model)
    max_tokens_default = default_max_tokens(model=model)
    openai_config = {
        'api_key': os.environ['OPENAI_API_KEY'],
        'show_usage': get_env('SHOW_USAGE', 'false').lower() == 'true',
        'stream': get_env('STREAM', 'true').lower() == 'true',
        'proxy': get_env('PROXY', None) or get_env('OPENAI_PROXY', None),
        'max_history_size': get_env('MAX_HISTORY_SIZE', 15, int),
        'max_conversation_age_minutes': get_env('MAX_CONVERSATION_AGE_MINUTES', 180, int),
        'assistant_prompt': get_env('ASSISTANT_PROMPT', 'You are a helpful assistant.'),
        'max_tokens': get_env('MAX_TOKENS', max_tokens_default, int),
        'n_choices': get_env('N_CHOICES', 1, int),
        'temperature': get_env('TEMPERATURE', 1.0, float),
        'image_model': get_env('IMAGE_MODEL', 'dall-e-2'),
        'image_quality': get_env('IMAGE_QUALITY', 'standard'),
        'image_style': get_env('IMAGE_STYLE', 'vivid'),
        'image_size': get_env('IMAGE_SIZE', '512x512'),
        'model': model,
        'enable_functions': get_env('ENABLE_FUNCTIONS', str(functions_available)).lower() == 'true',
        'functions_max_consecutive_calls': get_env('FUNCTIONS_MAX_CONSECUTIVE_CALLS', 10, int),
        'presence_penalty': get_env('PRESENCE_PENALTY', 0.0, float),
        'frequency_penalty': get_env('FREQUENCY_PENALTY', 0.0, float),
        'bot_language': get_env('BOT_LANGUAGE', 'en'),
        'show_plugins_used': get_env('SHOW_PLUGINS_USED', 'false').lower() == 'true',
        'whisper_prompt': get_env('WHISPER_PROMPT', ''),
        'vision_model': get_env('VISION_MODEL', 'gpt-4o'),
        'enable_vision_follow_up_questions': get_env('ENABLE_VISION_FOLLOW_UP_QUESTIONS', 'true').lower() == 'true',
        'vision_prompt': get_env('VISION_PROMPT', 'What is in this image'),
        'vision_detail': get_env('VISION_DETAIL', 'auto'),
        'vision_max_tokens': get_env('VISION_MAX_TOKENS', 300, int),
        'tts_model': get_env('TTS_MODEL', 'tts-1'),
        'tts_voice': get_env('TTS_VOICE', 'alloy'),
        'reasoning_effort': get_env('REASONING_EFFORT', 'none'),
        'verbosity': get_env('VERBOSITY', 'medium'),
        'enable_web_search': get_env('ENABLE_WEB_SEARCH', 'false').lower() == 'true',
        'enable_file_search': get_env('ENABLE_FILE_SEARCH', 'false').lower() == 'true',
        'file_search_vector_store_ids': get_env('FILE_SEARCH_VECTOR_STORE_IDS', ''),
        'enable_mcp': get_env('ENABLE_MCP', 'false').lower() == 'true',
        'mcp_server_label': get_env('MCP_SERVER_LABEL', 'default_mcp'),
        'mcp_server_url': get_env('MCP_SERVER_URL', ''),
        'mcp_server_description': get_env('MCP_SERVER_DESCRIPTION', ''),
        'enable_code_interpreter': get_env('ENABLE_CODE_INTERPRETER', 'false').lower() == 'true',
        'enable_computer_use': get_env('ENABLE_COMPUTER_USE', 'false').lower() == 'true',
        'tool_choice': get_env('TOOL_CHOICE', 'auto'),  # auto, required, or none
    }

    if openai_config['enable_functions'] and not functions_available:
        logging.error(f'ENABLE_FUNCTIONS is set to true, but the model {model} does not support it. '
                        'Please set ENABLE_FUNCTIONS to false or use a model that supports it.')
        exit(1)
    if os.environ.get('MONTHLY_USER_BUDGETS') is not None:
        logging.warning('The environment variable MONTHLY_USER_BUDGETS is deprecated. '
                        'Please use USER_BUDGETS with BUDGET_PERIOD instead.')
    if os.environ.get('MONTHLY_GUEST_BUDGET') is not None:
        logging.warning('The environment variable MONTHLY_GUEST_BUDGET is deprecated. '
                        'Please use GUEST_BUDGET with BUDGET_PERIOD instead.')

    telegram_config = {
        'token': os.environ['TELEGRAM_BOT_TOKEN'],
        'admin_user_ids': get_env('ADMIN_USER_IDS', '-'),
        'allowed_user_ids': get_env('ALLOWED_TELEGRAM_USER_IDS', '*'),
        'enable_quoting': get_env('ENABLE_QUOTING', 'true').lower() == 'true',
        'enable_image_generation': get_env('ENABLE_IMAGE_GENERATION', 'true').lower() == 'true',
        'enable_transcription': get_env('ENABLE_TRANSCRIPTION', 'true').lower() == 'true',
        'enable_vision': get_env('ENABLE_VISION', 'true').lower() == 'true',
        'enable_tts_generation': get_env('ENABLE_TTS_GENERATION', 'true').lower() == 'true',
        'budget_period': get_env('BUDGET_PERIOD', 'monthly').lower(),
        'user_budgets': get_env('USER_BUDGETS', get_env('MONTHLY_USER_BUDGETS', '*')),
        'guest_budget': get_env('GUEST_BUDGET', get_env('MONTHLY_GUEST_BUDGET', 100.0, float), float),
        'stream': get_env('STREAM', 'true').lower() == 'true',
        'proxy': get_env('PROXY', None) or get_env('TELEGRAM_PROXY', None),
        'voice_reply_transcript': get_env('VOICE_REPLY_WITH_TRANSCRIPT_ONLY', 'false').lower() == 'true',
        'voice_reply_prompts': get_env('VOICE_REPLY_PROMPTS', '').split(';'),
        'ignore_group_transcriptions': get_env('IGNORE_GROUP_TRANSCRIPTIONS', 'true').lower() == 'true',
        'ignore_group_vision': get_env('IGNORE_GROUP_VISION', 'true').lower() == 'true',
        'group_trigger_keyword': get_env('GROUP_TRIGGER_KEYWORD', ''),
        'token_price': get_env('TOKEN_PRICE', 0.002, float),
        'image_prices': get_env('IMAGE_PRICES', [0.016, 0.018, 0.02], parse_float_list),
        'vision_token_price': get_env('VISION_TOKEN_PRICE', 0.01, float),
        'image_receive_mode': get_env('IMAGE_FORMAT', "photo"),
        'tts_model': get_env('TTS_MODEL', 'tts-1'),
        'tts_prices': get_env('TTS_PRICES', [0.015, 0.030], parse_float_list),
        'transcription_price': get_env('TRANSCRIPTION_PRICE', 0.006, float),
        'bot_language': get_env('BOT_LANGUAGE', 'en'),
        'message_aggregation_delay': get_env('MESSAGE_AGGREGATION_DELAY', 1.5, float),  # seconds to wait for split message parts
    }

    plugin_config = {
        'plugins': get_env('PLUGINS', '').split(',')
    }

    # Setup and run ChatGPT and Telegram bot
    plugin_manager = PluginManager(config=plugin_config)
    openai_helper = OpenAIHelper(config=openai_config, plugin_manager=plugin_manager)
    telegram_bot = ChatGPTTelegramBot(config=telegram_config, openai=openai_helper)
    telegram_bot.run()


if __name__ == '__main__':
    main()
