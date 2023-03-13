import os.path
import pathlib
import json
from datetime import date

def year_month(date):
    # extract string of year-month from date, eg: '2023-03'
    return str(date)[:7]

class UsageTracker:
    """
    UsageTracker class
    Enables tracking of daily/monthly token usage per user.
    User files are stored as JSON in /token_usage directory.
    JSON example:
    {
        "user_name": "user_name",
        "current_cost": {
            "day": 0.45, 
            "month": 3.23, 
            "last_update": "2023-03-14"},
        "usage_history": {
            "chat_tokens": {
                "2023-03-13": 520,
                "2023-03-14": 1532
            },
            "transcription_seconds": {
                "2023-03-13": 125,
                "2023-03-14": 64
            },
            "number_images": {
                "2023-03-12": [0, 2, 3],
                "2023-03-13": [1, 2, 3],
                "2023-03-14": [0, 1, 2]
            }
        }
    }
    """

    def __init__(self, user_id, user_name, logs_dir="usage_logs"):
        """
        Initializes UsageTracker for a user with current date. 
        Loads usage data from usage log file.
        :param user_id: Telegram ID of the user
        :param user_name: Telegram user name
        :param logs_dir: path to directory of usage logs, default "usage_logs"
        """
        self.user_id = user_id
        self.logs_dir = logs_dir
        # path to usage file of given user
        self.user_file = f"{logs_dir}/{user_id}.json"
        
        if os.path.isfile(self.user_file):
            with open(self.user_file, "r") as file:
                self.usage = json.load(file)
        else:
            # ensure directory exists 
            pathlib.Path(logs_dir).mkdir(exist_ok=True)
            # create new dictionary for this user
            self.usage = {
                "user_name": user_name,
                "current_cost": {"day": 0.0, "month": 0.0, "last_update": str(date.today())},
                "usage_history": {"chat_tokens": {}, "transcription_seconds": {}, "number_images": {}}
            }

    # token usage functions:
    
    def add_chat_tokens(self, tokens, tokens_price=0.002):
        """
        Adds used tokens from a request to a users usage history.
        Updates current cost
        :param tokens: total tokens used in last request
        :param tokens_price: price per 1000 tokens
        """
        today = date.today()
        last_update = date.fromisoformat(self.usage["current_cost"]["last_update"])
        # add current cost, update new day
        if today == last_update:
            self.usage["current_cost"]["day"] += tokens * (tokens_price * 0.001)
            self.usage["current_cost"]["month"] += tokens * (tokens_price * 0.001)
        else:
            if today.month == last_update.month:
                self.usage["current_cost"]["month"] += tokens * (tokens_price * 0.001)
            else:
                self.usage["current_cost"]["month"] = tokens * (tokens_price * 0.001)
            self.usage["current_cost"]["day"] = tokens * (tokens_price * 0.001)
            self.usage["current_cost"]["last_update"] = str(today)

        # update usage_history
        if str(today) in self.usage["usage_history"]["chat_tokens"]:
            # add token usage to existing date
            self.usage["usage_history"]["chat_tokens"][str(today)] += tokens
        else:
            # create new entry for current month and day
            self.usage["usage_history"]["chat_tokens"][str(today)] = tokens
        
        # write updated token usage to user file
        with open(self.user_file, "w") as outfile:
            json.dump(self.usage, outfile)

    def get_token_usage(self, date=date.today()):
        if str(date) in self.usage["usage_history"]["chat_tokens"]:
            usage_day = self.usage["usage_history"]["chat_tokens"][str(date)]
        else:
            usage_day = 0
        month = str(date)[:7] # year-month as string
        usage_month = 0
        for date, tokens in self.usage["usage_history"]["chat_tokens"].items():
            if date.startswith(month):
                usage_month += tokens
        return usage_day, usage_month

    # transcription usage functions:

    def add_transcription_seconds(self, seconds):
        # TODO: implement
        pass

    def get_transcription_usage(self, date=date.today()):
        # TODO: implement
        pass

    @staticmethod
    def cost_transcription(seconds, minute_price=0.006):
        # cost of audio seconds transcribed, amount in USD
        # current price Whisper: $0.002/1000 tokens
        second_price = minute_price/60
        return seconds * second_price
    
    def get_transcription_seconds_and_cost(self, date=date.today(), minute_price=0.006):
        # TODO: implement
        pass
    
    # image usage functions:

    def add_image_request(self, seconds):
        # TODO: implement
        pass

    def get_image_count(self, date=date.today()):
        # TODO: implement
        pass

    @staticmethod
    def cost_images(image_counts, image_prices=[0.016, 0.018, 0.02]):
        # TODO: implement
        pass

    def get_image_counts_and_costs(self, date=date.today(), image_prices=[0.016, 0.018, 0.02]):
        # TODO: implement
        pass

    # general functions
    def get_current_cost(self):
        pass
    
    def get_all_stats(self, date=date.today(), token_price=0.002, minute_price=0.006, 
                      image_prices=[0.016, 0.018, 0.02]):
        # TODO: implement
        pass

"""
testing 
user = UsageTracker("hi", "my_name")
user.add_chat_tokens(12)
print(user.get_token_usage(date.fromisoformat('2023-05-03')))

"""
