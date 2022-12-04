import logging

import telegram.constants
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters


class ChatGPT3TelegramBot:
    def __init__(self, config, gpt3_bot):
        self.config = config
        self.gpt3_bot = gpt3_bot

    # Start the bot
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logging.info('Bot started')
        await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a Chat-GPT3 Bot, please talk to me!")

    # React to messages
    async def prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logging.info('New message received')
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING)
        response = self.gpt3_bot.get_chat_response(update.message.text)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response["message"])
        logging.info('Sent response')

    def run(self):
        application = ApplicationBuilder().token(self.config['telegram_bot_token']).build()

        start_handler = CommandHandler('start', self.start)
        prompt_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), self.prompt)

        application.add_handler(start_handler)
        application.add_handler(prompt_handler)

        application.run_polling()
