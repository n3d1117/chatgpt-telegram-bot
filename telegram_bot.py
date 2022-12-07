import logging

import telegram.constants
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters


class ChatGPT3TelegramBot:
    def __init__(self, config, gpt3_bot):
        self.config = config
        self.gpt3_bot = gpt3_bot
        self.disallowed_message = "Sorry, you are not allowed to use this bot. You can check out the source code at " \
                                  "https://github.com/n3d1117/chatgpt-telegram-bot"

    # Help menu
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("/start - Start the bot\n/reset - Reset conversation\n/help - Help menu\n\n"
                                        "Open source at https://github.com/n3d1117/chatgpt-telegram-bot")

    # Start the bot
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_allowed(update):
            logging.info(f'User {update.message.from_user.name} is not allowed to start the bot')
            await context.bot.send_message(chat_id=update.effective_chat.id, text=self.disallowed_message)
            return

        logging.info('Bot started')
        await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a Chat-GPT3 Bot, please talk to me!")

    # Reset the conversation
    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_allowed(update):
            logging.info(f'User {update.message.from_user.name} is not allowed to reset the bot')
            await context.bot.send_message(chat_id=update.effective_chat.id, text=self.disallowed_message)
            return

        logging.info('Resetting the conversation...')
        self.gpt3_bot.reset_chat()
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Done!")

    # React to messages
    async def prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_allowed(update):
            logging.info(f'User {update.message.from_user.name} is not allowed to use the bot')
            await context.bot.send_message(chat_id=update.effective_chat.id, text=self.disallowed_message)
            return

        logging.info(f'New message received from user {update.message.from_user.name}')
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING)
        response = self.get_chatgpt_response(update.message.text)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.message_id,
            text=response["message"],
            parse_mode=telegram.constants.ParseMode.MARKDOWN
        )

    def get_chatgpt_response(self, message) -> dict:
        try:
            response = self.gpt3_bot.get_chat_response(message)
            return response
        except Exception as e:
            logging.info(f'Error while getting the response: {e}')
            return {"message": "I'm having some trouble talking to you, please try again later."}

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logging.debug(f'Exception while handling an update: {context.error}')

    def is_allowed(self, update: Update) -> bool:
        return str(update.message.from_user.id) in self.config['allowed_chats']

    def run(self):
        application = ApplicationBuilder().token(self.config['telegram_bot_token']).build()

        application.add_handler(CommandHandler('start', self.start))
        application.add_handler(CommandHandler('reset', self.reset))
        application.add_handler(CommandHandler('help', self.help))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.prompt))

        application.add_error_handler(self.error_handler)

        application.run_polling(poll_interval=2.0, timeout=20)
