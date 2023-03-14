import logging
import os

from dotenv import load_dotenv

from openai_helper import OpenAIHelper
from telegram_bot import ChatGPT3TelegramBot


def main():
    # Read .env file
    load_dotenv()

    # Setup logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    # Check if the required environment variables are set
    required_values = ['TELEGRAM_BOT_TOKEN', 'OPENAI_API_KEY']
    missing_values = [value for value in required_values if os.environ.get(value) is None]
    if len(missing_values) > 0:
        logging.error(f'The following environment values are missing in your .env: {", ".join(missing_values)}')
        exit(1)

    # Setup configurations
    openai_config = {
        'api_key': os.environ['OPENAI_API_KEY'],
        'show_usage': os.environ.get('SHOW_USAGE', 'false').lower() == 'true',
        'proxy': os.environ.get('PROXY', None),
        'max_history_size': int(os.environ.get('MAX_HISTORY_SIZE', 10)),
        'max_conversation_age_minutes': int(os.environ.get('MAX_CONVERSATION_AGE_MINUTES', 180)),
        'assistant_prompt': os.environ.get('ASSISTANT_PROMPT', 'You are a helpful assistant.'),
        'max_tokens': int(os.environ.get('MAX_TOKENS', 1200)),

        # 'gpt-3.5-turbo' or 'gpt-3.5-turbo-0301'
        'model': 'gpt-3.5-turbo',

        # Number between 0 and 2. Higher values like 0.8 will make the output more random,
        # while lower values like 0.2 will make it more focused and deterministic.
        'temperature': 1,

        # How many chat completion choices to generate for each input message.
        'n_choices': 1,

        # Number between -2.0 and 2.0. Positive values penalize new tokens based on whether
        # they appear in the text so far, increasing the model's likelihood to talk about new topics.
        'presence_penalty': 0,

        # Number between -2.0 and 2.0. Positive values penalize new tokens based on their existing
        # frequency in the text so far, decreasing the model's likelihood to repeat the same line verbatim.
        'frequency_penalty': 0,

        # The DALL·E generated image size
        'image_size': '512x512'
    }

    telegram_config = {
        'token': os.environ['TELEGRAM_BOT_TOKEN'],
        'allowed_user_ids': os.environ.get('ALLOWED_TELEGRAM_USER_IDS', '*'),
        'monthly_user_budgets': os.environ.get('MONTHLY_USER_BUDGETS', '*'),
        'proxy': os.environ.get('PROXY', None),
        'voice_reply_transcript': os.environ.get('VOICE_REPLY_WITH_TRANSCRIPT_ONLY', 'true').lower() == 'true',
        'token_price': float(os.environ.get('TOKEN_PRICE', 0.002)),
        'image_prices': [float(i) for i in os.environ.get('IMAGE_PRICES',"0.016,0.018,0.02").split(",")],
        'transcription_price': float(os.environ.get('TOKEN_PRICE', 0.002)),
    }
    # Setup and run ChatGPT and Telegram bot
    openai_helper = OpenAIHelper(config=openai_config)
    telegram_bot = ChatGPT3TelegramBot(config=telegram_config, openai=openai_helper)
    telegram_bot.run()


if __name__ == '__main__':
    main()
