import logging
import os

from dotenv import load_dotenv
from asyncChatGPT.asyncChatGPT import Chatbot as ChatGPT3Bot
from telegram_bot import ChatGPT3TelegramBot


def main():
    load_dotenv()

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    if 'TELEGRAM_BOT_TOKEN' not in os.environ:
        logging.error('Telegram bot token not found in environment variables')
        exit(1)

    chatgpt_config = {
        'email': os.environ['OPENAI_EMAIL'],
        'password': os.environ['OPENAI_PASSWORD'],
        'proxy': os.environ.get('PROXY', ''),
    }
    telegram_config = {
        'token': os.environ['TELEGRAM_BOT_TOKEN'],
        'allowed_user_ids': os.environ.get('ALLOWED_TELEGRAM_USER_IDS', '*')
    }
    debug = os.environ.get('DEBUG', 'true').lower() == 'true'

    gpt3_bot = ChatGPT3Bot(config=chatgpt_config, debug=debug)
    telegram_bot = ChatGPT3TelegramBot(config=telegram_config, gpt3_bot=gpt3_bot)
    telegram_bot.run()


if __name__ == '__main__':
    main()
