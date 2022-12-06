import logging
import os
import time

from dotenv import load_dotenv
from revChatGPT.revChatGPT import Chatbot as ChatGPT3Bot
from telegram_bot import ChatGPT3TelegramBot


def main():
    load_dotenv()

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    chatgpt_config = {
        'email': os.environ['OPENAI_EMAIL'],
        'password': os.environ['OPENAI_PASSWORD'],
    }
    telegram_config = {
        'telegram_bot_token': os.environ['TELEGRAM_BOT_TOKEN']
    }

    gpt3_bot = ChatGPT3Bot(config=chatgpt_config)
    telegram_bot = ChatGPT3TelegramBot(config=telegram_config, gpt3_bot=gpt3_bot)
    telegram_bot.run()


if __name__ == '__main__':
    while True:
        try:
            main()
        except:
            logging.error('An error occurred, restarting...')
        time.sleep(5)