import json
import logging

from chat_gpt3_bot import ChatGPT3Bot
from telegram_bot import ChatGPT3TelegramBot


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    with open("config.json", "r") as f:
        config = json.load(f)

    gpt3_bot = ChatGPT3Bot(config=config)
    telegram_bot = ChatGPT3TelegramBot(config=config, gpt3_bot=gpt3_bot)
    telegram_bot.run()


if __name__ == '__main__':
    main()
