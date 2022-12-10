import logging
import os

from dotenv import load_dotenv
from asyncChatGPT.asyncChatGPT import Chatbot as ChatGPT3Bot
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
    required_values = ['TELEGRAM_BOT_TOKEN', 'OPENAI_EMAIL', 'OPENAI_PASSWORD']
    missing_values = [value for value in required_values if os.environ.get(value) is None]
    if len(missing_values) > 0:
        logging.error(f'The following environment values are missing in your .env: {", ".join(missing_values)}')
        exit(1)

    # Setup configuration
    chatgpt_config = {
        'email': os.environ['OPENAI_EMAIL'],
        'password': os.environ['OPENAI_PASSWORD']
    }
    telegram_config = {
        'token': os.environ['TELEGRAM_BOT_TOKEN'],
        'allowed_user_ids': os.environ.get('ALLOWED_TELEGRAM_USER_IDS', '*')
    }

    if os.environ.get('PROXY', None) is not None:
        chatgpt_config.update({'proxy': os.environ.get('PROXY')})

    debug = os.environ.get('DEBUG', 'true').lower() == 'true'

    # Setup and run ChatGPT and Telegram bot
    gpt3_bot = ChatGPT3Bot(config=chatgpt_config, debug=debug)
    telegram_bot = ChatGPT3TelegramBot(config=telegram_config, gpt3_bot=gpt3_bot)
    telegram_bot.run()


if __name__ == '__main__':
    main()
