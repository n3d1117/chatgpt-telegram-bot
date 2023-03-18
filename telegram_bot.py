import logging
import os

from telegram import constants
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, BotCommand
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, \
    filters, InlineQueryHandler, Application

from pydub import AudioSegment
from openai_helper import OpenAIHelper
from usage_tracker import UsageTracker


class ChatGPT3TelegramBot:
    """
    Class representing a Chat-GPT3 Telegram Bot.
    """

    def __init__(self, config: dict, openai: OpenAIHelper):
        """
        Initializes the bot with the given configuration and GPT-3 bot object.
        :param config: A dictionary containing the bot configuration
        :param openai: OpenAIHelper object
        """
        self.config = config
        self.openai = openai
        self.commands = [
            BotCommand(command='help', description='Show help message'),
            BotCommand(command='reset', description='Reset the conversation'),
            BotCommand(command='image', description='Generate image from prompt (e.g. /image cat)'),
            BotCommand(command='stats', description='Get your current usage statistics')
        ]
        self.disallowed_message = "Sorry, you are not allowed to use this bot. You can check out the source code at " \
                                  "https://github.com/n3d1117/chatgpt-telegram-bot"
        self.budget_limit_message = "Sorry, you have reached your monthly usage limit."
        self.usage = {}

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Shows the help menu.
        """
        commands = [f'/{command.command} - {command.description}' for command in self.commands]
        help_text = 'I\'m a ChatGPT bot, talk to me!' + \
                    '\n\n' + \
                    '\n'.join(commands) + \
                    '\n\n' + \
                    'Send me a voice message or file and I\'ll transcribe it for you!' + \
                    '\n\n' + \
                    "Open source at https://github.com/n3d1117/chatgpt-telegram-bot"
        await update.message.reply_text(help_text, disable_web_page_preview=True)


    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Returns token usage statistics for current day and month.
        """
        if not await self.is_allowed(update):
            logging.warning(f'User {update.message.from_user.name} is not allowed to request their usage statistics')
            await self.send_disallowed_message(update, context)
            return

        logging.info(f'User {update.message.from_user.name} requested their token usage statistics')
        
        user_id = update.message.from_user.id
        if user_id not in self.usage:
            self.usage[user_id] = UsageTracker(user_id, update.message.from_user.name)

        tokens_today, tokens_month = self.usage[user_id].get_current_token_usage()
        images_today, images_month = self.usage[user_id].get_current_image_count()
        transcribe_durations = self.usage[user_id].get_current_transcription_duration()
        cost_today, cost_month = self.usage[user_id].get_current_cost()
        
        usage_text = f"Today:\n"+\
                     f"{tokens_today} chat tokens used.\n"+\
                     f"{images_today} images generated.\n"+\
                     f"{transcribe_durations[0]} minutes and {transcribe_durations[1]} seconds transcribed.\n"+\
                     f"💰 For a total amount of ${cost_today:.2f}\n"+\
                     f"\n----------------------------\n\n"+\
                     f"This month:\n"+\
                     f"{tokens_month} chat tokens used.\n"+\
                     f"{images_month} images generated.\n"+\
                     f"{transcribe_durations[2]} minutes and {transcribe_durations[3]} seconds transcribed.\n"+\
                     f"💰 For a total amount of ${cost_month:.2f}"
        await update.message.reply_text(usage_text)

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Resets the conversation.
        """
        if not await self.is_allowed(update):
            logging.warning(f'User {update.message.from_user.name} is not allowed to reset the conversation')
            await self.send_disallowed_message(update, context)
            return

        logging.info(f'Resetting the conversation for user {update.message.from_user.name}...')

        chat_id = update.effective_chat.id
        self.openai.reset_chat_history(chat_id=chat_id)
        await context.bot.send_message(chat_id=chat_id, text='Done!')

    async def image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Generates an image for the given prompt using DALL·E APIs
        """
        if not await self.is_allowed(update):
            logging.warning(f'User {update.message.from_user.name} is not allowed to generate images')
            await self.send_disallowed_message(update, context)
            return

        if not await self.is_within_budget(update):
            logging.warning(f'User {update.message.from_user.name} reached their usage limit')
            await self.send_budget_reached_message(update, context)
            return
        
        chat_id = update.effective_chat.id
        image_query = update.message.text.replace('/image', '').strip()
        if image_query == '':
            await context.bot.send_message(chat_id=chat_id, text='Please provide a prompt! (e.g. /image cat)')
            return

        logging.info(f'New image generation request received from user {update.message.from_user.name}')

        await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.UPLOAD_PHOTO)
        try:
            image_url, image_size = self.openai.generate_image(prompt=image_query)
            await context.bot.send_photo(
                chat_id=chat_id,
                reply_to_message_id=update.message.message_id,
                photo=image_url
            )
            # add image request to users usage tracker
            user_id = update.message.from_user.id
            self.usage[user_id].add_image_request(image_size, self.config['image_prices'])
            # add guest chat request to guest usage tracker
            if str(user_id) not in self.config['allowed_user_ids'].split(','):
                self.usage["guests"].add_image_request(image_size, self.config['image_prices'])

        except Exception as e:
            logging.exception(e)
            await context.bot.send_message(
                chat_id=chat_id,
                reply_to_message_id=update.message.message_id,
                text=f'Failed to generate image: {str(e)}'
            )

    async def transcribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Transcribe audio messages.
        """
        if not await self.is_allowed(update):
            logging.warning(f'User {update.message.from_user.name} is not allowed to transcribe audio messages')
            await self.send_disallowed_message(update, context)
            return
        
        if not await self.is_within_budget(update):
            logging.warning(f'User {update.message.from_user.name} reached their usage limit')
            await self.send_budget_reached_message(update, context)
            return

        if self.is_group_chat(update) and self.config['ignore_group_transcriptions']:
            logging.info(f'Transcription coming from group chat, ignoring...')
            return  

        chat_id = update.effective_chat.id
        await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)

        filename = update.message.effective_attachment.file_unique_id
        filename_mp3 = f'{filename}.mp3'

        try:
            media_file = await context.bot.get_file(update.message.effective_attachment.file_id)
            await media_file.download_to_drive(filename)
        except Exception as e:
            logging.exception(e)
            await context.bot.send_message(
                chat_id=chat_id,
                reply_to_message_id=update.message.message_id,
                text=f'Failed to download audio file: {str(e)}'
            )
            return

        # detect and extract audio from the attachment with pydub
        try:
            audio_track = AudioSegment.from_file(filename)
            audio_track.export(filename_mp3, format="mp3")
            logging.info(f'New transcribe request received from user {update.message.from_user.name}')

        except Exception as e:
            logging.exception(e)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.message_id,
                text='Unsupported file type'
            )
            if os.path.exists(filename):
                os.remove(filename)
            return

        filename_mp3 = f'{filename}.mp3'

        user_id = update.message.from_user.id
        if user_id not in self.usage:
            self.usage[user_id] = UsageTracker(user_id, update.message.from_user.name)

        # send decoded audio to openai
        try:

            # Transcribe the audio file
            transcript = self.openai.transcribe(filename_mp3)

            # add transcription seconds to usage tracker
            transcription_price = self.config['transcription_price']
            self.usage[user_id].add_transcription_seconds(audio_track.duration_seconds, transcription_price)

            # add guest chat request to guest usage tracker
            allowed_user_ids = self.config['allowed_user_ids'].split(',')
            if str(user_id) not in allowed_user_ids:
                self.usage["guests"].add_transcription_seconds(audio_track.duration_seconds, transcription_price)

            if self.config['voice_reply_transcript']:

                # Split into chunks of 4096 characters (Telegram's message limit)
                transcript_output = f'_Transcript:_\n"{transcript}"'
                chunks = self.split_into_chunks(transcript_output)

                for index, transcript_chunk in enumerate(chunks):
                    await context.bot.send_message(
                        chat_id=chat_id,
                        reply_to_message_id=update.message.message_id if index == 0 else None,
                        text=transcript_chunk,
                        parse_mode=constants.ParseMode.MARKDOWN
                    )
            else:
                # Get the response of the transcript
                response = self.openai.get_chat_response(chat_id=chat_id, query=transcript)
                if not isinstance(response, tuple):
                    raise Exception(response)

                response, total_tokens = response

                # add chat request to users usage tracker
                self.usage[user_id].add_chat_tokens(total_tokens, self.config['token_price'])
                # add guest chat request to guest usage tracker
                if str(user_id) not in allowed_user_ids:
                    self.usage["guests"].add_chat_tokens(total_tokens, self.config['token_price'])

                # Split into chunks of 4096 characters (Telegram's message limit)
                transcript_output = f'_Transcript:_\n"{transcript}"\n\n_Answer:_\n{response}'
                chunks = self.split_into_chunks(transcript_output)

                for index, transcript_chunk in enumerate(chunks):
                    await context.bot.send_message(
                        chat_id=chat_id,
                        reply_to_message_id=update.message.message_id if index == 0 else None,
                        text=transcript_chunk,
                        parse_mode=constants.ParseMode.MARKDOWN
                    )

        except Exception as e:
            logging.exception(e)
            await context.bot.send_message(
                chat_id=chat_id,
                reply_to_message_id=update.message.message_id,
                text=f'Failed to transcribe text: {str(e)}'
            )
        finally:
            # Cleanup files
            if os.path.exists(filename_mp3):
                os.remove(filename_mp3)
            if os.path.exists(filename):
                os.remove(filename)

    async def prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        React to incoming messages and respond accordingly.
        """
        if not await self.is_allowed(update):
            logging.warning(f'User {update.message.from_user.name} is not allowed to use the bot')
            await self.send_disallowed_message(update, context)
            return

        if not await self.is_within_budget(update):
            logging.warning(f'User {update.message.from_user.name} reached their usage limit')
            await self.send_budget_reached_message(update, context)
            return
        
        logging.info(f'New message received from user {update.message.from_user.name}')
        chat_id = update.effective_chat.id
        user_id = update.message.from_user.id
        prompt = update.message.text

        if self.is_group_chat(update):
            trigger_keyword = self.config['group_trigger_keyword']
            if prompt.startswith(trigger_keyword):
                prompt = prompt[len(trigger_keyword):].strip()
            else:
                logging.warning('Message does not start with trigger keyword, ignoring...')
                return

        await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)

        response = self.openai.get_chat_response(chat_id=chat_id, query=prompt)
        if not isinstance(response, tuple):
            await context.bot.send_message(
                chat_id=chat_id,
                reply_to_message_id=update.message.message_id,
                text=response,
                parse_mode=constants.ParseMode.MARKDOWN
            )
            return

        response, total_tokens = response

        # add chat request to users usage tracker
        self.usage[user_id].add_chat_tokens(total_tokens, self.config['token_price'])
        # add guest chat request to guest usage tracker
        allowed_user_ids = self.config['allowed_user_ids'].split(',')
        if str(user_id) not in allowed_user_ids:
            self.usage["guests"].add_chat_tokens(total_tokens, self.config['token_price'])

        # Split into chunks of 4096 characters (Telegram's message limit)
        chunks = self.split_into_chunks(response)

        for index, chunk in enumerate(chunks):
            await context.bot.send_message(
                chat_id=chat_id,
                reply_to_message_id=update.message.message_id if index == 0 else None,
                text=chunk,
                parse_mode=constants.ParseMode.MARKDOWN
            )

    async def inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the inline query. This is run when you type: @botusername <query>
        """
        query = update.inline_query.query

        if query == "":
            return

        results = [
            InlineQueryResultArticle(
                id=query,
                title="Ask ChatGPT",
                input_message_content=InputTextMessageContent(query),
                description=query,
                thumb_url='https://user-images.githubusercontent.com/11541888/223106202-7576ff11-2c8e-408d-94ea-b02a7a32149a.png'
            )
        ]

        await update.inline_query.answer(results)

    async def send_disallowed_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Sends the disallowed message to the user.
        """
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=self.disallowed_message,
            disable_web_page_preview=True
        )

    async def send_budget_reached_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Sends the budget reached message to the user.
        """
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=self.budget_limit_message
        )

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handles errors in the telegram-python-bot library.
        """
        logging.debug(f'Exception while handling an update: {context.error}')

    def is_group_chat(self, update: Update) -> bool:
        """
        Checks if the message was sent from a group chat
        """
        return update.effective_chat.type in [
            constants.ChatType.GROUP,
            constants.ChatType.SUPERGROUP
        ]

    async def is_user_in_group(self, update: Update, user_id: int) -> bool:
        """
        Checks if user_id is a member of the group
        """
        member = await update.effective_chat.get_member(user_id)
        return member.status in [
            constants.ChatMemberStatus.OWNER,
            constants.ChatMemberStatus.ADMINISTRATOR,
            constants.ChatMemberStatus.MEMBER
        ]

    async def is_allowed(self, update: Update) -> bool:
        """
        Checks if the user is allowed to use the bot.
        """
        if self.config['allowed_user_ids'] == '*':
            return True

        allowed_user_ids = self.config['allowed_user_ids'].split(',')

        # Check if user is allowed
        if str(update.message.from_user.id) in allowed_user_ids:
            return True

        # Check if it's a group a chat with at least one authorized member
        if self.is_group_chat(update):
            for user in allowed_user_ids:
                if await self.is_user_in_group(update, user):
                    logging.info(f'{user} is a member. Allowing group chat message...')
                    return True
            logging.info(f'Group chat messages from user {update.message.from_user.name} are not allowed')

        return False

    async def is_within_budget(self, update: Update) -> bool:
        """
        Checks if the user reached their monthly usage limit.
        Initializes UsageTracker for user and guest when needed.
        """
        user_id = update.message.from_user.id
        if user_id not in self.usage:
            self.usage[user_id] = UsageTracker(user_id, update.message.from_user.name)

        if self.config['monthly_user_budgets'] == '*':
            return True

        allowed_user_ids = self.config['allowed_user_ids'].split(',')
        if str(user_id) in allowed_user_ids:
            # find budget for allowed user
            user_index = allowed_user_ids.index(str(user_id))
            user_budgets = self.config['monthly_user_budgets'].split(',')
            # check if user is included in budgets list
            if len(user_budgets) <= user_index:
                logging.warning(f'No budget set for user: {update.message.from_user.name} ({user_id}).')
                return False
            user_budget = float(user_budgets[user_index])
            cost_month = self.usage[user_id].get_current_cost()[1]
            # Check if allowed user is within budget
            return user_budget > cost_month

        # Check if group member is within budget
        if self.is_group_chat(update):
            for user in allowed_user_ids:
                if await self.is_user_in_group(update, user):
                    if 'guests' not in self.usage:
                        self.usage['guests'] = UsageTracker('guests', 'all guest users in group chats')
                    if self.config['monthly_guest_budget'] >= self.usage['guests'].get_current_cost()[1]:
                        return True
                    logging.warning('Monthly guest budget for group chats used up.')
                    return False
            logging.info(f'Group chat messages from user {update.message.from_user.name} are not allowed')
        return False

    def split_into_chunks(self, text: str, chunk_size: int = 4096) -> list[str]:
        """
        Splits a string into chunks of a given size.
        """
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    async def post_init(self, application: Application) -> None:
        """
        Post initialization hook for the bot.
        """
        await application.bot.set_my_commands(self.commands)

    def run(self):
        """
        Runs the bot indefinitely until the user presses Ctrl+C
        """
        application = ApplicationBuilder() \
            .token(self.config['token']) \
            .proxy_url(self.config['proxy']) \
            .get_updates_proxy_url(self.config['proxy']) \
            .post_init(self.post_init) \
            .build()

        application.add_handler(CommandHandler('reset', self.reset))
        application.add_handler(CommandHandler('help', self.help))
        application.add_handler(CommandHandler('image', self.image))
        application.add_handler(CommandHandler('start', self.help))
        application.add_handler(CommandHandler('stats', self.stats))
        application.add_handler(MessageHandler(
            filters.AUDIO | filters.VOICE | filters.Document.AUDIO |
            filters.VIDEO | filters.VIDEO_NOTE | filters.Document.VIDEO,
            self.transcribe))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.prompt))
        application.add_handler(InlineQueryHandler(self.inline_query, chat_types=[
            constants.ChatType.GROUP, constants.ChatType.SUPERGROUP
        ]))

        application.add_error_handler(self.error_handler)

        application.run_polling()
