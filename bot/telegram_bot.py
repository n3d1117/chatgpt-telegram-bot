from __future__ import annotations

import asyncio
import datetime
import logging
import os
import psycopg2

from db import Database
from uuid import uuid4
from telegram import BotCommandScopeAllGroupChats, Update, constants, LabeledPrice
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle
from telegram import InputTextMessageContent, BotCommand
from telegram.error import RetryAfter, TimedOut
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, \
    filters, InlineQueryHandler, CallbackQueryHandler, Application, ContextTypes, CallbackContext, ConversationHandler, PreCheckoutQueryHandler
from pydub import AudioSegment
from utils import is_group_chat, get_thread_id, message_text, wrap_with_indicator, split_into_chunks, \
    edit_message_with_retry, get_stream_cutoff_values, is_allowed, \
    get_reply_to_message_id, add_chat_request_to_usage_tracker, error_handler, is_in_trial, get_trial_access, \
    get_date_expiration, get_subscribe_access, frequency_check, censor_check
from openai_helper import OpenAIHelper, localized_text
from usage_tracker import UsageTracker


FEEDBACK = 1

class ChatGPTTelegramBot:
    """
    Class representing a ChatGPT Telegram Bot.
    """

    def __init__(self, db, config: dict, openai: OpenAIHelper):
        """
        Initializes the bot with the given configuration and GPT bot object.
        :param config: A dictionary containing the bot configuration
        :param openai: OpenAIHelper object
        """
        self.db = db
        self.config = config
        self.openai = openai
        bot_language = self.config['bot_language']
        self.subscribe_description = localized_text('subscribe_description', bot_language)
        self.commands = [
            BotCommand(command='help', description=localized_text('help_description', bot_language)),
            BotCommand(command='reset', description=localized_text('reset_description', bot_language)),
            BotCommand(command='stats', description=localized_text('stats_description', bot_language)),
            BotCommand(command='trial', description=localized_text('trial_description', bot_language)),
            BotCommand(command='subscribe', description=self.subscribe_description),
            BotCommand(command='feedback', description=localized_text('feedback_description', bot_language)),
            BotCommand(command='terms', description=localized_text('terms_description', bot_language))

        ]
        self.group_commands = [BotCommand(
            command='chat', description=localized_text('chat_description', bot_language)
        )] + self.commands
        self.disallowed_message_trial = localized_text('disallowed_trial', bot_language)
        self.disallowed_message_not_trial = localized_text('disallowed_not_trial', bot_language)
        self.already_used_trial = localized_text('already_used_trial', bot_language)
        self.not_used_trial = localized_text('not_used_trial', bot_language)
        self.rules_of_using = localized_text('rules_of_using', bot_language)
        self.budget_limit_message = localized_text('budget_limit', bot_language)
        self.success_activate_trial = localized_text('success_activate_trial', bot_language)
        self.subscribe_offer = localized_text('subscribe_offer', bot_language)
        self.success_activate_subscribtion = localized_text('success_activate_subscribtion', bot_language)
        self.frequency_message = localized_text('frequency_error', bot_language)
        self.censor_message = localized_text('censor_error', bot_language)
        self.usage = {}
        self.last_message = {}
        self.inline_queries_cache = {}
        self.last_message_time = {}
        query = "SELECT LOWER(word) FROM ban_words;"
        ban_bd = db.fetch_all(query, None)
        self.banned_words = [i[0] for i in ban_bd]

    async def prompt_wrapper(self, update, context):
        await self.prompt(update, context)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        db = self.db
        print("LOG: catch \start")
        user = update.effective_user
        user_id = user.id
        username = user.username
        first_name = user.first_name
        last_name = user.last_name
        date = update.message.date
        print(f"LOG: Get Username: {username} UID:{user_id}")
        print(f"LOG: date: {date}")
        date_format = date.strftime("%Y-%m-%d %H:%M:%S")
        try:
            query = f"SELECT * FROM users WHERE user_id = {user_id}"
            user_exist = db.fetch_one(query)
        except:
            logging.info(f'{username} tries to re-register')
        if user_exist == user_id:
            await self.help(update, context)
            print("Users already in base")
            return;
        else:
            print("Try add user");

        query = f"INSERT INTO users (user_id, date_creation, user_first_name, user_last_name) VALUES(%s, %s, %s, %s);"
        db.query_update(query, (user_id, date_format, first_name, last_name,))

        greetings_text = f"{first_name} " + localized_text("hello_text", self.config['bot_language'])
        await update.message.reply_text(greetings_text, disable_web_page_preview=True)

    async def help(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Shows the help menu.
        """
        commands = self.group_commands if is_group_chat(update) else self.commands
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
        logging.info(f'User {update.message.from_user.name} catch \stats command ')
        user_id = update.message.from_user.id
        if user_id not in self.usage:
            self.usage[user_id] = UsageTracker(user_id, update.message.from_user.name)
        bot_language = self.config['bot_language']
        db = self.db
        if not await self.check_time_delay(update, context):
            return
        if not await self.check_allowed(update, context):
            return
        logging.info(f'User {update.message.from_user.name} (id: {update.message.from_user.id}) '
                     f'requested their usage statistics')

        try:
            query = "SELECT date_start, date_expiration FROM users WHERE user_id = %s"
            list_date = db.fetch_all(query, (user_id,))
            start_date = list_date[0][0]
            end_date = list_date[0][1]
            rest_time = list_date[0][1] - datetime.datetime.now()
            stats_sub_text = (
                    localized_text('stats_sub', bot_language)[0] +
                    '\n\n' +
                    localized_text('stats_sub', bot_language)[1] + "{:02d}.{:02d}.{:02d}  {:02d}:{:02d}".format(
                start_date.day, start_date.month, start_date.year, start_date.hour, start_date.minute) + '\n' +
                    localized_text('stats_sub', bot_language)[2] + "{:02d}.{:02d}.{:02d}  {:02d}:{:02d}".format(
                end_date.day, end_date.month, end_date.year, end_date.hour, end_date.minute) + '\n' +
                    localized_text('stats_sub', bot_language)[3].format(rest_time.days, rest_time.seconds // 3600,
                                                                        rest_time.seconds % 3600 // 60) +
                    '\n\n' +
                    localized_text('stats_sub', bot_language)[4]
            )
            await update.message.reply_text(stats_sub_text, parse_mode=constants.ParseMode.MARKDOWN)
        except Exception as e:
            logging.exception(e)


    async def trial(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Offering and activating the trial subscription
        """
        logging.info(f'Offering trial for user {update.message.from_user.name} (id: {update.message.from_user.id})')
        db = self.db
        if await is_in_trial(db, update, context):
            await update.message.reply_text(self.already_used_trial)
        else: 
            activate_btn = [
                [InlineKeyboardButton('Получить бесплатный доступ', callback_data='activate_trial')]
            ]
            reply_markup = InlineKeyboardMarkup(activate_btn)
            await update.message.reply_text(self.not_used_trial, reply_markup=reply_markup)

    async def subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Offering and activating the full subscription
        """
        logging.info(f'Offering subscribe for user {update.message.from_user.name} (id: {update.message.from_user.id})')
        activate_btn = [
            [InlineKeyboardButton('Оплатить', callback_data='subscribe_access')]
        ]
        reply_markup = InlineKeyboardMarkup(activate_btn)
        await update.message.reply_text(self.subscribe_offer, reply_markup=reply_markup)
        await update.message.reply_text(self.rules_of_using)

    async def inline_query_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        db = self.db
        query = update.callback_query
        if query.data == "activate_trial":
            if await get_trial_access(query.from_user.id, db):
                date_exp = await get_date_expiration(query.from_user.id, db)
                await update.effective_message.reply_text(
                    message_thread_id=get_thread_id(update),
                    text = self.success_activate_trial % str(date_exp))
                
        elif query.data == "subscribe_access":
            chat_id = query.from_user.id
            title = "SympaBot Pro: Безлимитный доступ"
            description = self.subscribe_description
            payload = "Custom-Payload"
            currency = "RUB"
            price = 20000
            prices = [LabeledPrice("Test", price)]
            payment_provider = self.config['payment_provider']
            await context.bot.send_invoice(
                chat_id=chat_id, 
                title=title, 
                description=description, 
                payload=payload,
                provider_token=payment_provider, 
                currency=currency, 
                start_parameter="start", 
                prices=prices,
                need_email=True,
                send_email_to_provider=True,
                provider_data={
                    "receipt":{
                        "items":[
                            {
                                "description": "SympaBot Pro",
                                "quantity":"1.00",
                                "amount":{
                                    "value": "200.00",
                                    "currency": "RUB"
                                },
                                "vat_code": 1
                            }
                        ]
                    }
                }
            )

    async def precheckout_subscription_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.pre_checkout_query
        if query.invoice_payload == "Custom-Payload":
            await context.bot.answer_pre_checkout_query(query.id, ok=True)
        else:
            await context.bot.answer_pre_checkout_query(ok=False, error_message="Something went wrong...")

    async def successful_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        db = self.db
        if await get_subscribe_access(update.effective_chat.id, db):
            date_exp = await get_date_expiration(update.effective_chat.id, db)
            await update.effective_message.reply_text(
                message_thread_id=get_thread_id(update),
                text = self.success_activate_subscribtion % str(date_exp))     

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Resets the conversation.
        """
        logging.info(f'User {update.message.from_user.name} catch \ reset command ')
        db = self.db
        user_id = str(update.message.from_user.id)
        if not await self.check_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name} (id: {update.message.from_user.id}) '
                            f'is not allowed to reset the conversation')
            return

        logging.info(f'Resetting the conversation for user {update.message.from_user.name} '
                     f'(id: {update.message.from_user.id})...')

        chat_id = update.effective_chat.id
        reset_content = message_text(update.message)
        self.openai.reset_chat_history(chat_id=chat_id, content=reset_content)
        await update.effective_message.reply_text(
            message_thread_id=get_thread_id(update),
            text=localized_text('reset_done', self.config['bot_language'])
        )

    async def terms(self, update: Update, context: CallbackContext):
        """Send a message with the inline keyboard button that leads to the FEEDBACK state."""
        user_id = update.message.from_user.id
        if user_id not in self.usage:
            self.usage[user_id] = UsageTracker(user_id, update.message.from_user.name)
        bot_language = self.config['bot_language']
        if not await self.check_time_delay(update, context):
            return
        await update.message.reply_text(localized_text('terms_message', bot_language))

    async def feedback(self, update: Update, context: CallbackContext):
        """Send a message with the inline keyboard button that leads to the FEEDBACK state."""
        logging.info(f'User {update.message.from_user.name} catch \ feedback command ')
        user_id = update.message.from_user.id
        if user_id not in self.usage:
            self.usage[user_id] = UsageTracker(user_id, update.message.from_user.name)
        bot_language = self.config['bot_language']
        if not await self.check_time_delay(update, context):
            return
        await update.message.reply_text(localized_text('feedback_message', bot_language))
        return FEEDBACK

    async def feedback_response(self, update: Update, context: CallbackContext):
        """Handle the user's feedback message."""
        logging.info('Feedback response function called')
        if update.message is not None:
            feedback_message = update.message.text
            user_id = update.message.from_user.id
            bot_language = self.config['bot_language']
            try:
                db = self.db
                insert_query = "INSERT INTO feedback (user_id, feedback_message, feedback_date) VALUES(%s, %s, %s);"
                db.query_update(insert_query, (str(user_id), feedback_message, datetime.datetime.now()))
                response = localized_text('feedback_response', bot_language)
                await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
            except Exception as e:
                logging.exception(e)
        return ConversationHandler.END

    async def cancel(self, update: Update, context: CallbackContext):
        """End the conversation and go back to the regular state."""
        bot_language = self.config['bot_language']
        await update.message.reply_text(localized_text('cancel_state', bot_language))
        return ConversationHandler.END



    async def prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        React to incoming messages and respond accordingly.
        """
        if update.edited_message or not update.message or update.message.via_bot:
            return
        if not await self.check_time_delay(update, context):
            return
        if not await self.message_censor(update, context):
            return
        if not await self.check_allowed(update, context):
            return


        logging.info(
            f'New message received from user {update.message.from_user.name} (id: {update.message.from_user.id})')
        chat_id = update.effective_chat.id
        user_id = update.message.from_user.id
        prompt = message_text(update.message)

        self.last_message[chat_id] = prompt

        if is_group_chat(update):
            trigger_keyword = self.config['group_trigger_keyword']

            if prompt.lower().startswith(trigger_keyword.lower()) or update.message.text.lower().startswith('/chat'):
                if prompt.lower().startswith(trigger_keyword.lower()):
                    prompt = prompt[len(trigger_keyword):].strip()

                if update.message.reply_to_message and \
                        update.message.reply_to_message.text and \
                        update.message.reply_to_message.from_user.id != context.bot.id:
                    prompt = f'"{update.message.reply_to_message.text}" {prompt}'
            else:
                if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
                    logging.info('Message is a reply to the bot, allowing...')
                else:
                    logging.warning('Message does not start with trigger keyword, ignoring...')
                    return

        try:
            total_tokens = 0

            if self.config['stream']:
                async def _reply():
                    nonlocal total_tokens
                    await update.effective_message.reply_chat_action(
                        action=constants.ChatAction.TYPING,
                        message_thread_id=get_thread_id(update)
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

                        stream_chunks = split_into_chunks(content)
                        if len(stream_chunks) > 1:
                            content = stream_chunks[-1]
                            if stream_chunk != len(stream_chunks) - 1:
                                stream_chunk += 1
                                try:
                                    await edit_message_with_retry(context, chat_id, str(sent_message.message_id),
                                                                  stream_chunks[-2])
                                except:
                                    pass
                                try:
                                    sent_message = await update.effective_message.reply_text(
                                        message_thread_id=get_thread_id(update),
                                        text=content if len(content) > 0 else "..."
                                    )
                                except:
                                    pass
                                continue

                        cutoff = get_stream_cutoff_values(update, content)
                        cutoff += backoff

                        if i == 0:
                            try:
                                if sent_message is not None:
                                    await context.bot.delete_message(chat_id=sent_message.chat_id,
                                                                     message_id=sent_message.message_id)
                                sent_message = await update.effective_message.reply_text(
                                    message_thread_id=get_thread_id(update),
                                    reply_to_message_id=get_reply_to_message_id(self.config, update),
                                    text=content
                                )
                            except:
                                continue

                        elif abs(len(content) - len(prev)) > cutoff or tokens != 'not_finished':
                            prev = content

                            try:
                                use_markdown = tokens != 'not_finished'
                                await edit_message_with_retry(context, chat_id, str(sent_message.message_id),
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

                await wrap_with_indicator(update, context, _reply, constants.ChatAction.TYPING)

            else:
                async def _reply():
                    nonlocal total_tokens
                    response, total_tokens, responce_for_check = await self.openai.get_chat_response(chat_id=chat_id, query=prompt)

                    # Send response to censor
                    if not await self.message_censor(update, context, responce_for_check):
                        return

                    # Split into chunks of 4096 characters (Telegram's message limit)
                    chunks = split_into_chunks(response)

                    for index, chunk in enumerate(chunks):
                        try:
                            await update.effective_message.reply_text(
                                message_thread_id=get_thread_id(update),
                                reply_to_message_id=get_reply_to_message_id(self.config,
                                                                            update) if index == 0 else None,
                                text=chunk,
                                parse_mode=constants.ParseMode.MARKDOWN
                            )
                        except Exception:
                            try:
                                await update.effective_message.reply_text(
                                    message_thread_id=get_thread_id(update),
                                    reply_to_message_id=get_reply_to_message_id(self.config,
                                                                                update) if index == 0 else None,
                                    text=chunk
                                )
                            except Exception as exception:
                                raise exception

                await wrap_with_indicator(update, context, _reply, constants.ChatAction.TYPING)

            add_chat_request_to_usage_tracker(self.usage, self.config, user_id, total_tokens)

        except Exception as e:
            logging.exception(e)
            await update.effective_message.reply_text(
                message_thread_id=get_thread_id(update),
                reply_to_message_id=get_reply_to_message_id(self.config, update),
                text=f"{localized_text('chat_fail', self.config['bot_language'])} {str(e)}",
                parse_mode=constants.ParseMode.MARKDOWN
            )

    async def inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the inline query. This is run when you type: @botusername <query>
        """
        db = self.db
        query = update.inline_query.query
        if len(query) < 3:
            return
        if not await self.check_allowed(update, context, is_inline=True):
            return

        callback_data_suffix = "gpt:"
        result_id = str(uuid4())
        self.inline_queries_cache[result_id] = query
        callback_data = f'{callback_data_suffix}{result_id}'

        await self.send_inline_query_result(update, result_id, message_content=query, callback_data=callback_data)

    async def send_inline_query_result(self, update: Update, result_id, message_content, callback_data=""):
        """
        Send inline query result
        """
        db = self.db
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
        """
        Handle the callback query from the inline query result
        """
        logging.info('start handle_callback_inline_query')
        query = update.callback_query
        if query.data == 'Feedback':
            # Skip the callback if it's from the feedback button
            return

        db = self.db
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
                    await edit_message_with_retry(context, chat_id=None, message_id=inline_message_id,
                                                  text=f'{query}\n\n_{answer_tr}:_\n{error_message}',
                                                  is_inline=True)
                    return

                if self.config['stream']:
                    stream_response = self.openai.get_chat_response_stream(chat_id=user_id, query=query)
                    i = 0
                    prev = ''
                    backoff = 0
                    async for content, tokens in stream_response:
                        if len(content.strip()) == 0:
                            continue

                        cutoff = get_stream_cutoff_values(update, content)
                        cutoff += backoff

                        if i == 0:
                            try:
                                await edit_message_with_retry(context, chat_id=None,
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

                                await edit_message_with_retry(context, chat_id=None, message_id=inline_message_id,
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

                        if await self.message_censor(update, context, response):
                            print('Helllo2')
                            return

                        text_content = f'{query}\n\n_{answer_tr}:_\n{response}'

                        # We only want to send the first 4096 characters. No chunking allowed in inline mode.
                        text_content = text_content[:4096]
                        # print(response)

                        # Edit the original message with the generated content
                        await edit_message_with_retry(context, chat_id=None, message_id=inline_message_id,
                                                      text=text_content, is_inline=True)

                    await wrap_with_indicator(update, context, _send_inline_query_response,
                                              constants.ChatAction.TYPING, is_inline=True)

                add_chat_request_to_usage_tracker(self.usage, self.config, user_id, total_tokens)

        except Exception as e:
            logging.error(f'Failed to respond to an inline query via button callback: {e}')
            logging.exception(e)
            localized_answer = localized_text('chat_fail', self.config['bot_language'])
            await edit_message_with_retry(context, chat_id=None, message_id=inline_message_id,
                                          text=f"{query}\n\n_{answer_tr}:_\n{localized_answer} {str(e)}",
                                          is_inline=True)

    async def check_allowed(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                              is_inline=False) -> bool:
        """
        Checks if the user is allowed to use the bot
        :param update: Telegram update object
        :param context: Telegram context object
        :param is_inline: Boolean flag for inline queries
        :return: Boolean indicating if the user is allowed to use the bot
        """
        db = self.db
        name = update.inline_query.from_user.name if is_inline else update.message.from_user.name
        user_id = update.inline_query.from_user.id if is_inline else update.message.from_user.id
        if not await is_allowed(self.db, update, context, is_inline=is_inline) and await is_in_trial(self.db, update, context, is_inline=is_inline):
            logging.warning(f'User {name} (id: {user_id}) is not allowed to use the bot with trial')
            await self.send_disallowed_message(self.disallowed_message_trial, update, context, is_inline)
            return False
        elif not await is_allowed(self.db, update, context, is_inline=is_inline) and not await is_in_trial(self.db, update, context, is_inline=is_inline):
            logging.warning(f'User {name} (id: {user_id}) is not allowed to use the bot without trial')
            await self.send_disallowed_message(self.disallowed_message_not_trial, update, context, is_inline)
            return False
        return True

    async def check_time_delay(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                            is_inline=False) -> bool:
        name = update.inline_query.from_user.name if is_inline else update.message.from_user.name
        user_id = update.inline_query.from_user.id if is_inline else update.message.from_user.id
        if not frequency_check(self.config, self.usage, self.last_message_time, update, is_inline=is_inline):
            logging.warning(f'User {name} (id: {user_id}) violated the frequency of sending messages')
            await self.send_frequency_error_message(update, context, is_inline)
            return False
        self.last_message_time[user_id] = datetime.datetime.now()
        return True

    async def message_censor(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args,
                            is_inline=False) -> bool:
        db = self.db
        print('message_censor entry')
        # name = update.inline_query.from_user.name if is_inline else update.message.from_user.name
        # user_id = update.inline_query.from_user.id if is_inline else update.message.from_user.id
        print(args)
        if args:
            message = args[0].lower()
        else:
            message = message_text(update.message).lower()
        print(message)
        if censor_check(db, self.banned_words, self.config, self.usage, update, message, is_inline=is_inline):
            logging.warning(f'User message has been censored') # {name} (id: {user_id})
            await self.send_censor_message(update, context, is_inline)
            return False
        return True

    async def send_disallowed_message(self, message, update: Update, context: ContextTypes.DEFAULT_TYPE, is_inline=False):
        """
        Sends the disallowed message to the user.
        """
        if not is_inline:
            await update.effective_message.reply_text(
                message_thread_id=get_thread_id(update),
                text=message,
                disable_web_page_preview=True
            )
        else:
            result_id = str(uuid4())
            await self.send_inline_query_result(update, result_id, message_content=message)


    async def send_frequency_error_message(self, update: Update, _: ContextTypes.DEFAULT_TYPE, is_inline=False):
        """
        Sends the frequency error message to the user.
        """
        if not is_inline:
            await update.effective_message.reply_text(
                message_thread_id=get_thread_id(update),
                text=self.frequency_message
            )
        else:
            result_id = str(uuid4())
            await self.send_inline_query_result(update, result_id, message_content=self.frequency_message)

    async def send_censor_message(self, update: Update, _: ContextTypes.DEFAULT_TYPE, is_inline=False):
        """
        Sends the frequency error message to the user.
        """
        if not is_inline:
            await update.effective_message.reply_text(
                message_thread_id=get_thread_id(update),
                text=self.censor_message
            )
        else:
            result_id = str(uuid4())
            await self.send_inline_query_result(update, result_id, message_content=self.censor_message)

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
            .concurrent_updates(False) \
            .build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('feedback', self.feedback)],
            states={
                FEEDBACK: [MessageHandler(filters.TEXT & (~filters.COMMAND), self.feedback_response)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )

        application.add_handler(conv_handler)
        application.add_handler(CommandHandler('reset', self.reset))
        application.add_handler(CommandHandler('help', self.help))
        application.add_handler(CommandHandler('start', self.start))
        application.add_handler(CommandHandler('stats', self.stats))
        application.add_handler(CommandHandler('terms', self.terms))
        application.add_handler(CommandHandler('trial', self.trial))
        application.add_handler(CommandHandler('subscribe', self.subscribe))
        application.add_handler(CallbackQueryHandler(self.inline_query_handler))
        application.add_handler(PreCheckoutQueryHandler(self.precheckout_subscription_callback))
        application.add_handler(CommandHandler(
            'chat', self.prompt, filters=filters.ChatType.GROUP | filters.ChatType.SUPERGROUP)
        )
        application.add_handler(
            MessageHandler(filters.SUCCESSFUL_PAYMENT, self.successful_payment_callback)
        )
        # application.add_handler(MessageHandler(
        #     filters.AUDIO | filters.VOICE | filters.Document.AUDIO |
        #     filters.VIDEO | filters.VIDEO_NOTE | filters.Document.VIDEO,
        #     self.transcribe))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.prompt))
        application.add_handler(InlineQueryHandler(self.inline_query, chat_types=[
            constants.ChatType.GROUP, constants.ChatType.SUPERGROUP, constants.ChatType.PRIVATE
        ]))
        application.add_handler(CallbackQueryHandler(self.handle_callback_inline_query))

        application.add_error_handler(error_handler)

        application.run_polling()


