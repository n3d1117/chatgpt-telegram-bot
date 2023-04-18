from __future__ import annotations
import logging
import os
import itertools
import asyncio

import telegram
from uuid import uuid4
from telegram import constants, BotCommandScopeAllGroupChats
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle
from telegram import Message, MessageEntity, Update, InputTextMessageContent, BotCommand, ChatMember
from telegram.error import RetryAfter, TimedOut
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, \
    filters, InlineQueryHandler, CallbackQueryHandler, Application, CallbackContext

from pydub import AudioSegment
from openai_helper import OpenAIHelper, localized_text
from usage_tracker import UsageTracker


def message_text(message: Message) -> str:
    """
    Returns the text of a message, excluding any bot commands.
    """
    message_txt = message.text
    if message_txt is None:
        return ''

    for _, text in sorted(message.parse_entities([MessageEntity.BOT_COMMAND]).items(),
                          key=(lambda item: item[0].offset)):
        message_txt = message_txt.replace(text, '').strip()

    return message_txt if len(message_txt) > 0 else ''


class ChatGPTTelegramBot:
    """
    Class representing a ChatGPT Telegram Bot.
    """
    # Mapping of budget period to cost period
    budget_cost_map = {
        "monthly": "cost_month",
        "daily": "cost_today",
        "all-time": "cost_all_time"
    }

    def __init__(self, config: dict, openai: OpenAIHelper):
        """
        Initializes the bot with the given configuration and GPT bot object.
        :param config: A dictionary containing the bot configuration
        :param openai: OpenAIHelper object
        """
        self.config = config
        self.openai = openai
        bot_language = self.config['bot_language']
        self.commands = [
            BotCommand(command='help', description=localized_text('help_description', bot_language)),
            BotCommand(command='reset', description=localized_text('reset_description', bot_language)),
            BotCommand(command='image', description=localized_text('image_description', bot_language)),
            BotCommand(command='stats', description=localized_text('stats_description', bot_language)),
            BotCommand(command='resend', description=localized_text('resend_description', bot_language))
        ]
        self.group_commands = [
                                  BotCommand(command='chat',
                                             description=localized_text('chat_description', bot_language))
                              ] + self.commands
        self.disallowed_message = localized_text('disallowed', bot_language)
        self.budget_limit_message = localized_text('budget_limit', bot_language)
        self.usage = {}
        self.last_message = {}
        self.inline_queries_cache = {}

    async def help(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Shows the help menu.
        """
        commands = self.group_commands if self.is_group_chat(update) else self.commands
        commands_description = [f'/{command.command} - {command.description}' for command in commands]
        bot_language = self.config['bot_language']
        help_text = (
                localized_text('help_text', bot_language)[0] +
                '\n\n' +
                '\n'.join(commands_description) +
                '\n\n' +
                localized_text('help_text', bot_language)[1] +
                '\n\n' +
                localized_text('help_text', bot_language)[2]
        )
        await update.message.reply_text(help_text, disable_web_page_preview=True)

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Returns token usage statistics for current day and month.
        """
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name} (id: {update.message.from_user.id}) '
                            f'is not allowed to request their usage statistics')
            await self.send_disallowed_message(update, context)
            return

        logging.info(f'User {update.message.from_user.name} (id: {update.message.from_user.id}) '
                     f'requested their usage statistics')

        user_id = update.message.from_user.id
        if user_id not in self.usage:
            self.usage[user_id] = UsageTracker(user_id, update.message.from_user.name)

        tokens_today, tokens_month = self.usage[user_id].get_current_token_usage()
        images_today, images_month = self.usage[user_id].get_current_image_count()
        (transcribe_minutes_today, transcribe_seconds_today, transcribe_minutes_month,
         transcribe_seconds_month) = self.usage[user_id].get_current_transcription_duration()
        current_cost = self.usage[user_id].get_current_cost()

        chat_id = update.effective_chat.id
        chat_messages, chat_token_length = self.openai.get_conversation_stats(chat_id)
        remaining_budget = self.get_remaining_budget(update)
        bot_language = self.config['bot_language']
        text_current_conversation = (
            f"*{localized_text('stats_conversation', bot_language)[0]}*:\n"
            f"{chat_messages} {localized_text('stats_conversation', bot_language)[1]}\n"
            f"{chat_token_length} {localized_text('stats_conversation', bot_language)[2]}\n"
            f"----------------------------\n"
        )
        text_today = (
            f"*{localized_text('usage_today', bot_language)}:*\n"
            f"{tokens_today} {localized_text('stats_tokens', bot_language)}\n"
            f"{images_today} {localized_text('stats_images', bot_language)}\n"
            f"{transcribe_minutes_today} {localized_text('stats_transcribe', bot_language)[0]} "
            f"{transcribe_seconds_today} {localized_text('stats_transcribe', bot_language)[1]}\n"
            f"{localized_text('stats_total', bot_language)}{current_cost['cost_today']:.2f}\n"
            f"----------------------------\n"
        )
        text_month = (
            f"*{localized_text('usage_month', bot_language)}:*\n"
            f"{tokens_month} {localized_text('stats_tokens', bot_language)}\n"
            f"{images_month} {localized_text('stats_images', bot_language)}\n"
            f"{transcribe_minutes_month} {localized_text('stats_transcribe', bot_language)[0]} "
            f"{transcribe_seconds_month} {localized_text('stats_transcribe', bot_language)[1]}\n"
            f"{localized_text('stats_total', bot_language)}{current_cost['cost_month']:.2f}"
        )
        # text_budget filled with conditional content
        text_budget = "\n\n"
        budget_period = self.config['budget_period']
        if remaining_budget < float('inf'):
            text_budget += (
                f"{localized_text('stats_budget', bot_language)}"
                f"{localized_text(budget_period, bot_language)}: "
                f"${remaining_budget:.2f}.\n"
            )
        # add OpenAI account information for admin request
        if self.is_admin(user_id):
            text_budget += (
                f"{localized_text('stats_openai', bot_language)}"
                f"{self.openai.get_billing_current_month():.2f}"
            )

        usage_text = text_current_conversation + text_today + text_month + text_budget
        await update.message.reply_text(usage_text, parse_mode=constants.ParseMode.MARKDOWN)

    async def resend(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Resend the last request
        """
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}  (id: {update.message.from_user.id})'
                            f' is not allowed to resend the message')
            await self.send_disallowed_message(update, context)
            return

        chat_id = update.effective_chat.id
        if chat_id not in self.last_message:
            logging.warning(f'User {update.message.from_user.name} (id: {update.message.from_user.id})'
                            f' does not have anything to resend')
            await update.effective_message.reply_text(
                message_thread_id=self.get_thread_id(update),
                text=localized_text('resend_failed', self.config['bot_language'])
            )
            return

        # Update message text, clear self.last_message and send the request to prompt
        logging.info(f'Resending the last prompt from user: {update.message.from_user.name} '
                     f'(id: {update.message.from_user.id})')
        with update.message._unfrozen() as message:
            message.text = self.last_message.pop(chat_id)

        await self.prompt(update=update, context=context)

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Resets the conversation.
        """
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name} (id: {update.message.from_user.id}) '
                            f'is not allowed to reset the conversation')
            await self.send_disallowed_message(update, context)
            return

        logging.info(f'Resetting the conversation for user {update.message.from_user.name} '
                     f'(id: {update.message.from_user.id})...')

        chat_id = update.effective_chat.id
        reset_content = message_text(update.message)
        self.openai.reset_chat_history(chat_id=chat_id, content=reset_content)
        await update.effective_message.reply_text(
           message_thread_id=self.get_thread_id(update),
           text=localized_text('reset_done', self.config['bot_language'])
        )

    async def image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Generates an image for the given prompt using DALL·E APIs
        """
        if not self.config['enable_image_generation'] or not await self.check_allowed_and_within_budget(update,
                                                                                                        context):
            return

        chat_id = update.effective_chat.id
        image_query = message_text(update.message)
        if image_query == '':
            await update.effective_message.reply_text(
               message_thread_id=self.get_thread_id(update),
               text=localized_text('image_no_prompt', self.config['bot_language'])
            )
            return

        logging.info(f'New image generation request received from user {update.message.from_user.name} '
                     f'(id: {update.message.from_user.id})')

        async def _generate():
            try:
                image_url, image_size = await self.openai.generate_image(prompt=image_query)
                await update.effective_message.reply_photo(
                    reply_to_message_id=self.get_reply_to_message_id(update),
                    photo=image_url
                )
                # add image request to users usage tracker
                user_id = update.message.from_user.id
                self.usage[user_id].add_image_request(image_size, self.config['image_prices'])
                # add guest chat request to guest usage tracker
                if str(user_id) not in self.config['allowed_user_ids'].split(',') and 'guests' in self.usage:
                    self.usage["guests"].add_image_request(image_size, self.config['image_prices'])

            except Exception as e:
                logging.exception(e)
                await update.effective_message.reply_text(
                    message_thread_id=self.get_thread_id(update),
                    reply_to_message_id=self.get_reply_to_message_id(update),
                    text=f"{localized_text('image_fail', self.config['bot_language'])}: {str(e)}",
                    parse_mode=constants.ParseMode.MARKDOWN
                )

        await self.wrap_with_indicator(update, context, _generate, constants.ChatAction.UPLOAD_PHOTO)

    async def transcribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Transcribe audio messages.
        """
        if not self.config['enable_transcription'] or not await self.check_allowed_and_within_budget(update, context):
            return

        if self.is_group_chat(update) and self.config['ignore_group_transcriptions']:
            logging.info(f'Transcription coming from group chat, ignoring...')
            return

        chat_id = update.effective_chat.id
        filename = update.message.effective_attachment.file_unique_id

        async def _execute():
            filename_mp3 = f'{filename}.mp3'
            bot_language = self.config['bot_language']
            try:
                media_file = await context.bot.get_file(update.message.effective_attachment.file_id)
                await media_file.download_to_drive(filename)
            except Exception as e:
                logging.exception(e)
                await update.effective_message.reply_text(
                    message_thread_id=self.get_thread_id(update),
                    reply_to_message_id=self.get_reply_to_message_id(update),
                    text=(
                        f"{localized_text('media_download_fail', bot_language)[0]}: "
                        f"{str(e)}. {localized_text('media_download_fail', bot_language)[1]}"
                    ),
                    parse_mode=constants.ParseMode.MARKDOWN
                )
                return

            # detect and extract audio from the attachment with pydub
            try:
                audio_track = AudioSegment.from_file(filename)
                audio_track.export(filename_mp3, format="mp3")
                logging.info(f'New transcribe request received from user {update.message.from_user.name} '
                             f'(id: {update.message.from_user.id})')

            except Exception as e:
                logging.exception(e)
                await update.effective_message.reply_text(
                    message_thread_id=self.get_thread_id(update),
                    reply_to_message_id=self.get_reply_to_message_id(update),
                    text=localized_text('media_type_fail', bot_language)
                )
                if os.path.exists(filename):
                    os.remove(filename)
                return

            user_id = update.message.from_user.id
            if user_id not in self.usage:
                self.usage[user_id] = UsageTracker(user_id, update.message.from_user.name)

            # send decoded audio to openai
            try:

                # Transcribe the audio file
                transcript = await self.openai.transcribe(filename_mp3)

                # add transcription seconds to usage tracker
                transcription_price = self.config['transcription_price']
                self.usage[user_id].add_transcription_seconds(audio_track.duration_seconds, transcription_price)

                # add guest chat request to guest usage tracker
                allowed_user_ids = self.config['allowed_user_ids'].split(',')
                if str(user_id) not in allowed_user_ids and 'guests' in self.usage:
                    self.usage["guests"].add_transcription_seconds(audio_track.duration_seconds, transcription_price)

                if self.config['voice_reply_transcript']:

                    # Split into chunks of 4096 characters (Telegram's message limit)
                    transcript_output = f"_{localized_text('transcript', bot_language)}:_\n\"{transcript}\""
                    chunks = self.split_into_chunks(transcript_output)

                    for index, transcript_chunk in enumerate(chunks):
                        await update.effective_message.reply_text(
                            message_thread_id=self.get_thread_id(update),
                            reply_to_message_id=self.get_reply_to_message_id(update) if index == 0 else None,
                            text=transcript_chunk,
                            parse_mode=constants.ParseMode.MARKDOWN
                        )
                else:
                    # Get the response of the transcript
                    response, total_tokens = await self.openai.get_chat_response(chat_id=chat_id, query=transcript)

                    # add chat request to users usage tracker
                    self.usage[user_id].add_chat_tokens(total_tokens, self.config['token_price'])
                    # add guest chat request to guest usage tracker
                    if str(user_id) not in allowed_user_ids and 'guests' in self.usage:
                        self.usage["guests"].add_chat_tokens(total_tokens, self.config['token_price'])

                    # Split into chunks of 4096 characters (Telegram's message limit)
                    transcript_output = (
                        f"_{localized_text('transcript', bot_language)}:_\n\"{transcript}\"\n\n"
                        f"_{localized_text('answer', bot_language)}:_\n{response}"
                    )
                    chunks = self.split_into_chunks(transcript_output)

                    for index, transcript_chunk in enumerate(chunks):
                        await update.effective_message.reply_text(
                            message_thread_id=self.get_thread_id(update),
                            reply_to_message_id=self.get_reply_to_message_id(update) if index == 0 else None,
                            text=transcript_chunk,
                            parse_mode=constants.ParseMode.MARKDOWN
                        )

            except Exception as e:
                logging.exception(e)
                await update.effective_message.reply_text(
                    message_thread_id=self.get_thread_id(update),
                    reply_to_message_id=self.get_reply_to_message_id(update),
                    text=f"{localized_text('transcribe_fail', bot_language)}: {str(e)}",
                    parse_mode=constants.ParseMode.MARKDOWN
                )
            finally:
                # Cleanup files
                if os.path.exists(filename_mp3):
                    os.remove(filename_mp3)
                if os.path.exists(filename):
                    os.remove(filename)

        await self.wrap_with_indicator(update, context, _execute, constants.ChatAction.TYPING)

    async def prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        React to incoming messages and respond accordingly.
        """
        if update.edited_message or not update.message or update.message.via_bot:
            return

        if not await self.check_allowed_and_within_budget(update, context):
            return

        logging.info(
            f'New message received from user {update.message.from_user.name} (id: {update.message.from_user.id})')
        chat_id = update.effective_chat.id
        user_id = update.message.from_user.id
        prompt = message_text(update.message)
        self.last_message[chat_id] = prompt

        if self.is_group_chat(update):
            trigger_keyword = self.config['group_trigger_keyword']
            if prompt.lower().startswith(trigger_keyword.lower()):
                prompt = prompt[len(trigger_keyword):].strip()
            else:
                if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
                    logging.info('Message is a reply to the bot, allowing...')
                else:
                    logging.warning('Message does not start with trigger keyword, ignoring...')
                    return

        try:
            total_tokens = 0

            if self.config['stream']:
                await update.effective_message.reply_chat_action(
                    action=constants.ChatAction.TYPING,
                    message_thread_id=self.get_thread_id(update)
                )

                stream_response = self.openai.get_chat_response_stream(chat_id=chat_id, query=prompt)
                i = 0
                prev = ''
                sent_message = None
                backoff = 0
                stream_chunk = 0

                async for content, tokens in stream_response:
                    if len(content.strip()) == 0:
                        continue

                    stream_chunks = self.split_into_chunks(content)
                    if len(stream_chunks) > 1:
                        content = stream_chunks[-1]
                        if stream_chunk != len(stream_chunks) - 1:
                            stream_chunk += 1
                            try:
                                await self.edit_message_with_retry(context, chat_id, str(sent_message.message_id),
                                                                   stream_chunks[-2])
                            except:
                                pass
                            try:
                                sent_message = await update.effective_message.reply_text(
                                    message_thread_id=self.get_thread_id(update),
                                    text=content if len(content) > 0 else "..."
                                )
                            except:
                                pass
                            continue

                    cutoff = self.get_stream_cutoff_values(update, content)
                    cutoff += backoff

                    if i == 0:
                        try:
                            if sent_message is not None:
                                await context.bot.delete_message(chat_id=sent_message.chat_id,
                                                                 message_id=sent_message.message_id)
                            sent_message = await update.effective_message.reply_text(
                                message_thread_id=self.get_thread_id(update),
                                reply_to_message_id=self.get_reply_to_message_id(update),
                                text=content
                            )
                        except:
                            continue

                    elif abs(len(content) - len(prev)) > cutoff or tokens != 'not_finished':
                        prev = content

                        try:
                            use_markdown = tokens != 'not_finished'
                            await self.edit_message_with_retry(context, chat_id, str(sent_message.message_id),
                                                               text=content, markdown=use_markdown)

                        except RetryAfter as e:
                            backoff += 5
                            await asyncio.sleep(e.retry_after)
                            continue

                        except TimedOut:
                            backoff += 5
                            await asyncio.sleep(0.5)
                            continue

                        except Exception:
                            backoff += 5
                            continue

                        await asyncio.sleep(0.01)

                    i += 1
                    if tokens != 'not_finished':
                        total_tokens = int(tokens)

            else:
                async def _reply():
                    nonlocal total_tokens
                    response, total_tokens = await self.openai.get_chat_response(chat_id=chat_id, query=prompt)

                    # Split into chunks of 4096 characters (Telegram's message limit)
                    chunks = self.split_into_chunks(response)

                    for index, chunk in enumerate(chunks):
                        try:
                            await update.effective_message.reply_text(
                                message_thread_id=self.get_thread_id(update),
                                reply_to_message_id=self.get_reply_to_message_id(update) if index == 0 else None,
                                text=chunk,
                                parse_mode=constants.ParseMode.MARKDOWN
                            )
                        except Exception:
                            try:
                                await update.effective_message.reply_text(
                                    message_thread_id=self.get_thread_id(update),
                                    reply_to_message_id=self.get_reply_to_message_id(update) if index == 0 else None,
                                    text=chunk
                                )
                            except Exception as exception:
                                raise exception

                await self.wrap_with_indicator(update, context, _reply, constants.ChatAction.TYPING)

            self.add_chat_request_to_usage_tracker(user_id, total_tokens)

        except Exception as e:
            logging.exception(e)
            await update.effective_message.reply_text(
                message_thread_id=self.get_thread_id(update),
                reply_to_message_id=self.get_reply_to_message_id(update),
                text=f"{localized_text('chat_fail', self.config['bot_language'])} {str(e)}",
                parse_mode=constants.ParseMode.MARKDOWN
            )

    async def inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the inline query. This is run when you type: @botusername <query>
        """
        query = update.inline_query.query
        if len(query) < 3:
            return
        if not await self.check_allowed_and_within_budget(update, context, is_inline=True):
            return

        callback_data_suffix = "gpt:"
        result_id = str(uuid4())
        self.inline_queries_cache[result_id] = query
        callback_data = f'{callback_data_suffix}{result_id}'

        await self.send_inline_query_result(update, result_id, message_content=query, callback_data=callback_data)

    async def send_inline_query_result(self, update: Update, result_id, message_content, callback_data=""):
        try:
            reply_markup = None
            bot_language = self.config['bot_language']
            if callback_data:
                reply_markup = InlineKeyboardMarkup([[
                    InlineKeyboardButton(text=f'🤖 {localized_text("answer_with_chatgpt", bot_language)}',
                                         callback_data=callback_data)
                ]])

            inline_query_result = InlineQueryResultArticle(
                id=result_id,
                title=localized_text("ask_chatgpt", bot_language),
                input_message_content=InputTextMessageContent(message_content),
                description=message_content,
                thumb_url='https://user-images.githubusercontent.com/11541888/223106202-7576ff11-2c8e-408d-94ea'
                          '-b02a7a32149a.png',
                reply_markup=reply_markup
            )

            await update.inline_query.answer([inline_query_result], cache_time=0)
        except Exception as e:
            logging.error(f'An error occurred while generating the result card for inline query {e}')

    async def handle_callback_inline_query(self, update: Update, context: CallbackContext):
        callback_data = update.callback_query.data
        user_id = update.callback_query.from_user.id
        inline_message_id = update.callback_query.inline_message_id
        name = update.callback_query.from_user.name
        callback_data_suffix = "gpt:"
        query = ""
        bot_language = self.config['bot_language']
        answer_tr = localized_text("answer", bot_language)
        loading_tr = localized_text("loading", bot_language)

        try:
            if callback_data.startswith(callback_data_suffix):
                unique_id = callback_data.split(':')[1]
                total_tokens = 0

                # Retrieve the prompt from the cache
                query = self.inline_queries_cache.get(unique_id)
                if query:
                    self.inline_queries_cache.pop(unique_id)
                else:
                    error_message = (
                        f'{localized_text("error", bot_language)}. '
                        f'{localized_text("try_again", bot_language)}'
                    )
                    await self.edit_message_with_retry(context, chat_id=None, message_id=inline_message_id,
                                                       text=f'{query}\n\n_{answer_tr}:_\n{error_message}',
                                                       is_inline=True)
                    return

                if self.config['stream']:
                    stream_response = self.openai.get_chat_response_stream(chat_id=user_id, query=query)
                    i = 0
                    prev = ''
                    sent_message = None
                    backoff = 0
                    async for content, tokens in stream_response:
                        if len(content.strip()) == 0:
                            continue

                        cutoff = self.get_stream_cutoff_values(update, content)
                        cutoff += backoff

                        if i == 0:
                            try:
                                if sent_message is not None:
                                    await self.edit_message_with_retry(context, chat_id=None,
                                                                       message_id=inline_message_id,
                                                                       text=f'{query}\n\n{answer_tr}:\n{content}',
                                                                       is_inline=True)
                            except:
                                continue

                        elif abs(len(content) - len(prev)) > cutoff or tokens != 'not_finished':
                            prev = content
                            try:
                                use_markdown = tokens != 'not_finished'
                                divider = '_' if use_markdown else ''
                                text = f'{query}\n\n{divider}{answer_tr}:{divider}\n{content}'

                                # We only want to send the first 4096 characters. No chunking allowed in inline mode.
                                text = text[:4096]

                                await self.edit_message_with_retry(context, chat_id=None, message_id=inline_message_id,
                                                                   text=text, markdown=use_markdown, is_inline=True)

                            except RetryAfter as e:
                                backoff += 5
                                await asyncio.sleep(e.retry_after)
                                continue
                            except TimedOut:
                                backoff += 5
                                await asyncio.sleep(0.5)
                                continue
                            except Exception:
                                backoff += 5
                                continue

                            await asyncio.sleep(0.01)

                        i += 1
                        if tokens != 'not_finished':
                            total_tokens = int(tokens)

                else:
                    async def _send_inline_query_response():
                        nonlocal total_tokens
                        # Edit the current message to indicate that the answer is being processed
                        await context.bot.edit_message_text(inline_message_id=inline_message_id,
                                                            text=f'{query}\n\n_{answer_tr}:_\n{loading_tr}',
                                                            parse_mode=constants.ParseMode.MARKDOWN)

                        logging.info(f'Generating response for inline query by {name}')
                        response, total_tokens = await self.openai.get_chat_response(chat_id=user_id, query=query)

                        text_content = f'{query}\n\n_{answer_tr}:_\n{response}'

                        # We only want to send the first 4096 characters. No chunking allowed in inline mode.
                        text_content = text_content[:4096]

                        # Edit the original message with the generated content
                        await self.edit_message_with_retry(context, chat_id=None, message_id=inline_message_id,
                                                           text=text_content, is_inline=True)

                    await self.wrap_with_indicator(update, context, _send_inline_query_response,
                                                   constants.ChatAction.TYPING, is_inline=True)

                self.add_chat_request_to_usage_tracker(user_id, total_tokens)

        except Exception as e:
            logging.error(f'Failed to respond to an inline query via button callback: {e}')
            logging.exception(e)
            localized_answer = localized_text('chat_fail', self.config['bot_language'])
            await self.edit_message_with_retry(context, chat_id=None, message_id=inline_message_id,
                                               text=f"{query}\n\n_{answer_tr}:_\n{localized_answer} {str(e)}",
                                               is_inline=True)

    async def edit_message_with_retry(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int | None,
                                      message_id: str, text: str, markdown: bool = True, is_inline: bool = False):
        """
        Edit a message with retry logic in case of failure (e.g. broken markdown)
        :param context: The context to use
        :param chat_id: The chat id to edit the message in
        :param message_id: The message id to edit
        :param text: The text to edit the message with
        :param markdown: Whether to use markdown parse mode
        :param is_inline: Whether the message to edit is an inline message
        :return: None
        """
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=int(message_id) if not is_inline else None,
                inline_message_id=message_id if is_inline else None,
                text=text,
                parse_mode=constants.ParseMode.MARKDOWN if markdown else None
            )
        except telegram.error.BadRequest as e:
            if str(e).startswith("Message is not modified"):
                return
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=int(message_id) if not is_inline else None,
                    inline_message_id=message_id if is_inline else None,
                    text=text
                )
            except Exception as e:
                logging.warning(f'Failed to edit message: {str(e)}')
                raise e

        except Exception as e:
            logging.warning(str(e))
            raise e

    async def wrap_with_indicator(self, update: Update, context: CallbackContext, coroutine,
                                  chat_action: constants.ChatAction = "", is_inline=False):
        """
        Wraps a coroutine while repeatedly sending a chat action to the user.
        """
        task = context.application.create_task(coroutine(), update=update)
        while not task.done():
            if not is_inline:
                context.application.create_task(
                    update.effective_chat.send_action(chat_action, message_thread_id=self.get_thread_id(update))
                )
            try:
                await asyncio.wait_for(asyncio.shield(task), 4.5)
            except asyncio.TimeoutError:
                pass

    async def send_disallowed_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, is_inline=False):
        """
        Sends the disallowed message to the user.
        """
        if not is_inline:
            await update.effective_message.reply_text(
                message_thread_id=self.get_thread_id(update),
                text=self.disallowed_message,
                disable_web_page_preview=True
            )
        else:
            result_id = str(uuid4())
            await self.send_inline_query_result(update, result_id, message_content=self.disallowed_message)

    async def send_budget_reached_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, is_inline=False):
        """
        Sends the budget reached message to the user.
        """
        if not is_inline:
            await update.effective_message.reply_text(
                message_thread_id=self.get_thread_id(update),
                text=self.budget_limit_message
            )
        else:
            result_id = str(uuid4())
            await self.send_inline_query_result(update, result_id, message_content=self.budget_limit_message)

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handles errors in the telegram-python-bot library.
        """
        logging.error(f'Exception while handling an update: {context.error}')

    def get_thread_id(self, update: Update) -> int | None:
        """
        Gets the message thread id for the update, if any
        """
        if update.effective_message and update.effective_message.is_topic_message:
            return update.effective_message.message_thread_id
        return None

    def get_stream_cutoff_values(self, update: Update, content: str) -> int:
        """
        Gets the stream cutoff values for the message length
        """
        if self.is_group_chat(update):
            # group chats have stricter flood limits
            return 180 if len(content) > 1000 else 120 if len(content) > 200 else 90 if len(
                content) > 50 else 50
        else:
            return 90 if len(content) > 1000 else 45 if len(content) > 200 else 25 if len(
                content) > 50 else 15

    def is_group_chat(self, update: Update) -> bool:
        """
        Checks if the message was sent from a group chat
        """
        if not update.effective_chat:
            return False
        return update.effective_chat.type in [
            constants.ChatType.GROUP,
            constants.ChatType.SUPERGROUP
        ]

    async def is_user_in_group(self, update: Update, context: CallbackContext, user_id: int) -> bool:
        """
        Checks if user_id is a member of the group
        """
        try:
            chat_member = await context.bot.get_chat_member(update.message.chat_id, user_id)
            return chat_member.status in [ChatMember.OWNER, ChatMember.ADMINISTRATOR, ChatMember.MEMBER]
        except telegram.error.BadRequest as e:
            if str(e) == "User not found":
                return False
            else:
                raise e
        except Exception as e:
            raise e

    async def is_allowed(self, update: Update, context: CallbackContext, is_inline=False) -> bool:
        """
        Checks if the user is allowed to use the bot.
        """
        if self.config['allowed_user_ids'] == '*':
            return True

        user_id = update.inline_query.from_user.id if is_inline else update.message.from_user.id
        if self.is_admin(user_id):
            return True
        name = update.inline_query.from_user.name if is_inline else update.message.from_user.name
        allowed_user_ids = self.config['allowed_user_ids'].split(',')
        # Check if user is allowed
        if str(user_id) in allowed_user_ids:
            return True
        # Check if it's a group a chat with at least one authorized member
        if not is_inline and self.is_group_chat(update):
            admin_user_ids = self.config['admin_user_ids'].split(',')
            for user in itertools.chain(allowed_user_ids, admin_user_ids):
                if not user.strip():
                    continue
                if await self.is_user_in_group(update, context, user):
                    logging.info(f'{user} is a member. Allowing group chat message...')
                    return True
            logging.info(f'Group chat messages from user {name} '
                         f'(id: {user_id}) are not allowed')
        return False

    def is_admin(self, user_id: int, log_no_admin=False) -> bool:
        """
        Checks if the user is the admin of the bot.
        The first user in the user list is the admin.
        """
        if self.config['admin_user_ids'] == '-':
            if log_no_admin:
                logging.info('No admin user defined.')
            return False

        admin_user_ids = self.config['admin_user_ids'].split(',')

        # Check if user is in the admin user list
        if str(user_id) in admin_user_ids:
            return True

        return False

    def get_user_budget(self, user_id) -> float | None:
        """
        Get the user's budget based on their user ID and the bot configuration.
        :param user_id: User id
        :return: The user's budget as a float, or None if the user is not found in the allowed user list
        """

        # no budget restrictions for admins and '*'-budget lists
        if self.is_admin(user_id) or self.config['user_budgets'] == '*':
            return float('inf')

        user_budgets = self.config['user_budgets'].split(',')
        if self.config['allowed_user_ids'] == '*':
            # same budget for all users, use value in first position of budget list
            if len(user_budgets) > 1:
                logging.warning('multiple values for budgets set with unrestricted user list '
                                'only the first value is used as budget for everyone.')
            return float(user_budgets[0])

        allowed_user_ids = self.config['allowed_user_ids'].split(',')
        if str(user_id) in allowed_user_ids:
            user_index = allowed_user_ids.index(str(user_id))
            if len(user_budgets) <= user_index:
                logging.warning(f'No budget set for user id: {user_id}. Budget list shorter than user list.')
                return 0.0
            return float(user_budgets[user_index])
        return None

    def get_remaining_budget(self, update: Update, is_inline=False) -> float:
        """
        Calculate the remaining budget for a user based on their current usage.
        :param update: Telegram update object
        :param is_inline: Boolean flag for inline queries
        :return: The remaining budget for the user as a float
        """
        user_id = update.inline_query.from_user.id if is_inline else update.message.from_user.id
        name = update.inline_query.from_user.name if is_inline else update.message.from_user.name
        if user_id not in self.usage:
            self.usage[user_id] = UsageTracker(user_id, name)

        # Get budget for users
        user_budget = self.get_user_budget(user_id)
        budget_period = self.config['budget_period']
        if user_budget is not None:
            cost = self.usage[user_id].get_current_cost()[self.budget_cost_map[budget_period]]
            return user_budget - cost

        # Get budget for guests
        if 'guests' not in self.usage:
            self.usage['guests'] = UsageTracker('guests', 'all guest users in group chats')
        cost = self.usage['guests'].get_current_cost()[self.budget_cost_map[budget_period]]
        return self.config['guest_budget'] - cost

    def is_within_budget(self, update: Update, is_inline=False) -> bool:
        """
        Checks if the user reached their usage limit.
        Initializes UsageTracker for user and guest when needed.
        :param update: Telegram update object
        :param is_inline: Boolean flag for inline queries
        :return: Boolean indicating if the user has a positive budget
        """
        user_id = update.inline_query.from_user.id if is_inline else update.message.from_user.id
        name = update.inline_query.from_user.name if is_inline else update.message.from_user.name
        if user_id not in self.usage:
            self.usage[user_id] = UsageTracker(user_id, name)

        remaining_budget = self.get_remaining_budget(update, is_inline=is_inline)

        return remaining_budget > 0

    async def check_allowed_and_within_budget(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                              is_inline=False) -> bool:
        """
        Checks if the user is allowed to use the bot and if they are within their budget
        :param update: Telegram update object
        :param context: Telegram context object
        :param is_inline: Boolean flag for inline queries
        :return: Boolean indicating if the user is allowed to use the bot
        """
        name = update.inline_query.from_user.name if is_inline else update.message.from_user.name
        user_id = update.inline_query.from_user.id if is_inline else update.message.from_user.id

        if not await self.is_allowed(update, context, is_inline=is_inline):
            logging.warning(f'User {name} (id: {user_id}) '
                            f'is not allowed to use the bot')
            await self.send_disallowed_message(update, context, is_inline)
            return False
        if not self.is_within_budget(update, is_inline=is_inline):
            logging.warning(f'User {name} (id: {user_id}) '
                            f'reached their usage limit')
            await self.send_budget_reached_message(update, context, is_inline)
            return False

        return True

    def add_chat_request_to_usage_tracker(self, user_id, used_tokens):
        try:
            # add chat request to users usage tracker
            self.usage[user_id].add_chat_tokens(used_tokens, self.config['token_price'])
            # add guest chat request to guest usage tracker
            allowed_user_ids = self.config['allowed_user_ids'].split(',')
            if str(user_id) not in allowed_user_ids and 'guests' in self.usage:
                self.usage["guests"].add_chat_tokens(used_tokens, self.config['token_price'])
        except Exception as e:
            logging.warning(f'Failed to add tokens to usage_logs: {str(e)}')
            pass

    def get_reply_to_message_id(self, update: Update):
        """
        Returns the message id of the message to reply to
        :param update: Telegram update object
        :return: Message id of the message to reply to, or None if quoting is disabled
        """
        if self.config['enable_quoting'] or self.is_group_chat(update):
            return update.message.message_id
        return None

    def split_into_chunks(self, text: str, chunk_size: int = 4096) -> list[str]:
        """
        Splits a string into chunks of a given size.
        """
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    async def post_init(self, application: Application) -> None:
        """
        Post initialization hook for the bot.
        """
        await application.bot.set_my_commands(self.group_commands, scope=BotCommandScopeAllGroupChats())
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
            .concurrent_updates(True) \
            .build()

        application.add_handler(CommandHandler('reset', self.reset))
        application.add_handler(CommandHandler('help', self.help))
        application.add_handler(CommandHandler('image', self.image))
        application.add_handler(CommandHandler('start', self.help))
        application.add_handler(CommandHandler('stats', self.stats))
        application.add_handler(CommandHandler('resend', self.resend))
        application.add_handler(CommandHandler(
            'chat', self.prompt, filters=filters.ChatType.GROUP | filters.ChatType.SUPERGROUP)
        )
        application.add_handler(MessageHandler(
            filters.AUDIO | filters.VOICE | filters.Document.AUDIO |
            filters.VIDEO | filters.VIDEO_NOTE | filters.Document.VIDEO,
            self.transcribe))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.prompt))
        application.add_handler(InlineQueryHandler(self.inline_query, chat_types=[
            constants.ChatType.GROUP, constants.ChatType.SUPERGROUP, constants.ChatType.PRIVATE
        ]))
        application.add_handler(CallbackQueryHandler(self.handle_callback_inline_query))

        application.add_error_handler(self.error_handler)

        application.run_polling()
