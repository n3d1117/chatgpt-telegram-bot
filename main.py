import logging
import os

from dotenv import load_dotenv
from revChatGPT.V1 import AsyncChatbot as ChatGPT3Bot

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
    required_values = ['TELEGRAM_BOT_TOKEN']
    missing_values = [value for value in required_values if os.environ.get(value) is None]
    if len(missing_values) > 0:
        logging.error(f'The following environment values are missing in your .env: {", ".join(missing_values)}')
        exit(1)

    # Setup configuration
    chatgpt_config: dict[str, str | bool] = {
        'email': os.environ.get('OPENAI_EMAIL'),
        'password': os.environ.get('OPENAI_PASSWORD')
    } if os.environ.get('OPENAI_EMAIL') is not None else {
        'session_token': os.environ.get('OPENAI_SESSION_TOKEN')
    } if os.environ.get('OPENAI_SESSION_TOKEN') is not None else {
        'access_token': os.environ.get('OPENAI_ACCESS_TOKEN')
    } if os.environ.get('OPENAI_ACCESS_TOKEN') is not None else None

    if chatgpt_config is None:
        logging.error('PLease provide one of the authentication methods: OPENAI_EMAIL,OPENAI_PASSWORD | OPENAI_SESSION_TOKEN | OPENAI_ACCESS_TOKEN')
        exit(1)

    telegram_config = {
        'token': os.environ['TELEGRAM_BOT_TOKEN'],
        'allowed_user_ids': os.environ.get('ALLOWED_TELEGRAM_USER_IDS', '*'),
        'use_stream': os.environ.get('USE_STREAM', 'true').lower() == 'true'
    }

    if os.environ.get('PROXY', None) is not None:
        chatgpt_config.update({'proxy': os.environ.get('PROXY')})

    # Setup and run ChatGPT and Telegram bot
    gpt3_bot = ChatGPT3Bot(config=chatgpt_config)

    telegram_bot = ChatGPT3TelegramBot(config=telegram_config, gpt3_bot=gpt3_bot)
    telegram_bot.run()


if __name__ == '__main__':
    main()
