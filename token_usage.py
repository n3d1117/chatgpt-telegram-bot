import os.path
import pathlib
import json
from datetime import date
from itertools import chain

def year_month(date):
    # extract string of year-month from date, eg: '2023-03'
    return str(date)[:7]

def add_token_usage(user_id, tokens):
    """
    Adds used tokens from a request to a users usage file.
    Enables tracking of daily/monthly token usage per user.
    User files are stored as JSON in /token_usage directory.
    JSON schema:
    {'year-month':{'day': [tokens, tokens, ...], ...}, ...}
    :param user_id: Telegram user ID
    :param tokens: total tokens used in last request
    """
    # path to usage file of given user
    user_file = f"token_usage/{user_id}.json"
    # current year-month as string
    month = year_month(date.today())
    # current day as string, no leading zero
    day = str(date.today().day)

    if os.path.isfile(user_file):
        with open(user_file, "r") as infile:
            usage = json.load(infile)
        if month in usage:
            if day in usage[month]:
                # add token usage to current month and day
                usage[month][day].append(tokens)
            else:
                # create new entry for current day
                usage[month][day] = [tokens]
        else:
            # create new entry for current month and day
            usage[month] = {day: [tokens]}
    else:
        # ensure directory exists 
        pathlib.Path("token_usage").mkdir(exist_ok=True)
        # create new dictionary for this user and add used tokens
        usage = {month: {day: [tokens]}}

    # write updated token usage to user file
    with open(user_file, "w") as outfile:
        json.dump(usage, outfile)

def get_token_usage(user_id, date=date.today()):
    """
    Sums tokens used per day and per month of given date.
    Returns tuple of both values.
    :param user_id: Telegram user ID
    :param date: datetime.date object, default today
    """
    
    # path to usage file of given user
    user_file = f"token_usage/{user_id}.json"
    # year-month as string
    month = year_month(date)
    # day as string, no leading zero
    day = str(date.day)

    if os.path.isfile(user_file):
        with open(user_file, "r") as infile:
            usage = json.load(infile)
        usage_day = sum(usage[month][day])
        usage_month = sum(chain.from_iterable(list(usage[month].values())))
        return(usage_day, usage_month)
    else:
        return(0, 0)
    
def cost_tokens(tokens, price_1k_tokens=0.002):
    """
    cost of token amount in USD
    current price gpt-3.5-turbo: $0.002/1000 tokens
    :param tokens: number of tokens
    :param price_1k_tokens: price of 1000 tokens (https://openai.com/pricing)
    """
    return tokens*(price_1k_tokens/1000)