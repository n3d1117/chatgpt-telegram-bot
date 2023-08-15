from __future__ import annotations
from db import Database

import asyncio
import itertools
import logging

import telegram
from telegram import Message, MessageEntity, Update, ChatMember, constants
from telegram.ext import CallbackContext, ContextTypes

from usage_tracker import UsageTracker

from datetime import datetime, timedelta
import Levenshtein


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


def get_thread_id(update: Update) -> int | None:
    """
    Gets the message thread id for the update, if any
    """
    if update.effective_message and update.effective_message.is_topic_message:
        return update.effective_message.message_thread_id
    return None


def get_stream_cutoff_values(update: Update, content: str) -> int:
    """
    Gets the stream cutoff values for the message length
    """
    if is_group_chat(update):
        # group chats have stricter flood limits
        return 180 if len(content) > 1000 else 120 if len(content) > 200 \
            else 90 if len(content) > 50 else 50
    return 90 if len(content) > 1000 else 45 if len(content) > 200 \
        else 25 if len(content) > 50 else 15


def is_group_chat(update: Update) -> bool:
    """
    Checks if the message was sent from a group chat
    """
    if not update.effective_chat:
        return False
    return update.effective_chat.type in [
        constants.ChatType.GROUP,
        constants.ChatType.SUPERGROUP
    ]


def split_into_chunks(text: str, chunk_size: int = 4096) -> list[str]:
    """
    Splits a string into chunks of a given size.
    """
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


async def wrap_with_indicator(update: Update, context: CallbackContext, coroutine,
                              chat_action: constants.ChatAction = "", is_inline=False):
    """
    Wraps a coroutine while repeatedly sending a chat action to the user.
    """
    task = context.application.create_task(coroutine(), update=update)
    while not task.done():
        if not is_inline:
            context.application.create_task(
                update.effective_chat.send_action(chat_action, message_thread_id=get_thread_id(update))
            )
        try:
            await asyncio.wait_for(asyncio.shield(task), 4.5)
        except asyncio.TimeoutError:
            pass


async def edit_message_with_retry(context: ContextTypes.DEFAULT_TYPE, chat_id: int | None,
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


async def error_handler(_: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles errors in the telegram-python-bot library.
    """
    logging.error(f'Exception while handling an update: {context.error}')


async def get_date_expiration(user_id, db):
    """Получаем дату окончания подписки, если она вообще есть"""
    try:
        date_exp = db.fetch_one("SELECT date_expiration FROM users WHERE user_id = %s", (str(user_id),))
    except:
        error_handler()
    if date_exp is not None:
        return date_exp
    return None

async def get_trial_access(user_id, db):
    trial_access_query = "UPDATE users SET trial_flag = 'Y', date_expiration = %s, date_start = %s, subscription_id = 2 WHERE user_id = %s"
    date_exp = await set_date_expiration(3, datetime.now())
    try:
        check_res = db.query_update(trial_access_query, (date_exp, datetime.now(), str(user_id),), "User %s got trial access for 3 days" % user_id)
    except:
        error_handler()

    if check_res != None:
        return True
    return False

async def get_subscribe_access(user_id, db):
    subscription_access_query = "UPDATE users SET trial_flag = 'Y', date_expiration = %s, date_start = %s, subscription_id = 1 WHERE user_id = %s"
    
    if await get_date_expiration(user_id, db) is not None:
        date_exp = await set_date_expiration(30, await get_date_expiration(user_id, db))
    else: 
        date_exp = await set_date_expiration(30, datetime.now())

    try:
        check_res = db.query_update(subscription_access_query, (date_exp, datetime.now(), str(user_id),), "User %s got subscription access for 30 days" % user_id)
    except:
        error_handler()
    if check_res != None:
        return True
    return False

async def set_date_expiration(days, temp_date_exp):
    today = datetime.now()
    if(temp_date_exp >= today):
        dp = today + timedelta(days=days)
    else:
        dp = temp_date_exp + timedelta(days=days)

    return str(datetime(dp.year, dp.month, dp.day, dp.hour, dp.minute))

async def is_allowed(db, update: Update, context: CallbackContext, is_inline=False) -> bool:
    """
    Date Expiration Check
    """
    user_id = update.inline_query.from_user.id if is_inline else update.message.from_user.id
    today = datetime.now()
    try:
        date_exp = db.fetch_one("SELECT date_expiration FROM users WHERE user_id = %s", (str(user_id),))
    except Exception as e:
        logging.error(f'Database error while performing extraction {e}')
    if date_exp is not None and date_exp >= today:
        return True
    return False

async def is_in_trial(db, update: Update, context: CallbackContext, is_inline=False):
    """
    Trial Flag Check
    """
    user_id = update.callback_query.from_user.id if is_inline else update.message.from_user.id
    request_on_user = "SELECT trial_flag FROM users WHERE user_id = %s"
    try:
        user_trial = db.fetch_one(request_on_user, (str(user_id),))
    except Exception as e:
        logging.error(f'Database error while performing extraction {e}')
    if user_trial == "N":
        return False
    return True



def frequency_check(config, usage, last_message_time, update: Update, is_inline=False) -> bool:
    """
    checking the frequency of sending messages by the user
    :param config: The bot configuration object
    :param usage: The usage tracker object
    :param update: Telegram update object
    :param is_inline: Boolean flag for inline queries
    :return: If the user did not send a message earlier than time_delay
    """
    user_id = update.inline_query.from_user.id if is_inline else update.message.from_user.id
    name = update.inline_query.from_user.name if is_inline else update.message.from_user.name
    if user_id not in usage:
        usage[user_id] = UsageTracker(user_id, name)
    time_delay = config['time_delay']

    if user_id not in last_message_time:
        return True
    elif last_message_time[user_id] + timedelta(seconds=time_delay) < datetime.now():
        return True
    return False


def censor_check(db, banned_words, config, usage, update: Update, message, is_inline=False) -> bool:
    """
    checking the censor for messages by the user and Open AI
    :param config: The bot configuration object
    :param usage: The usage tracker object
    :param update: Telegram update object
    :param is_inline: Boolean flag for inline queries
    :return: True if the message contains banned words, otherwise False
    """
    words = message.split()  # Splitting the message into words
    query = "SELECT word FROM ban_words WHERE LOWER(word) = ANY(%s);"
    result = db.fetch_all(query, (words,))
    return len(result) > 0  # Return True if any banned words are found, otherwise False
    # for banned_word in banned_words:
    #     for word in words:
    #         if Levenshtein.distance(word, banned_word) <= 1:
    #             return True
    # return False

def is_admin(config, user_id: int, log_no_admin=False) -> bool:
    """
    Checks if the user is the admin of the bot.
    The first user in the user list is the admin.
    """
    if config['admin_user_ids'] == '-':
        if log_no_admin:
            logging.info('No admin user defined.')
        return False

    admin_user_ids = config['admin_user_ids'].split(',')

    # Check if user is in the admin user list
    if str(user_id) in admin_user_ids:
        return True

    return False

def add_chat_request_to_usage_tracker(usage, config, user_id, used_tokens):
    """
    Add chat request to usage tracker
    :param usage: The usage tracker object
    :param config: The bot configuration object
    :param user_id: The user id
    :param used_tokens: The number of tokens used
    """
    try:
        # add chat request to users usage tracker
        usage[user_id].add_chat_tokens(used_tokens, config['token_price'])
        # add guest chat request to guest usage tracker
    except Exception as e:
        logging.warning(f'Failed to add tokens to usage_logs: {str(e)}')
        pass


def get_reply_to_message_id(config, update: Update):
    """
    Returns the message id of the message to reply to
    :param config: Bot configuration object
    :param update: Telegram update object
    :return: Message id of the message to reply to, or None if quoting is disabled
    """
    if config['enable_quoting'] or is_group_chat(update):
        return update.message.message_id
    return None



