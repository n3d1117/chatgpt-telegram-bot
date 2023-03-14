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
    Enables tracking of daily/monthly usage per user.
    User files are stored as JSON in /usage_logs directory.
    JSON example:
    {
        "user_name": "@user_name",
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
        :param logs_dir: path to directory of usage logs, defaults to "usage_logs"
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
        """Adds used tokens from a request to a users usage history and updates current cost
        :param tokens: total tokens used in last request
        :param tokens_price: price per 1000 tokens, defaults to 0.002
        """
        today = date.today()
        last_update = date.fromisoformat(self.usage["current_cost"]["last_update"])
        # add current cost, update new day
        if today == last_update:
            self.usage["current_cost"]["day"] += round(tokens * tokens_price / 1000, 6)
            self.usage["current_cost"]["month"] += round(tokens * tokens_price / 1000, 6)
        else:
            if today.month == last_update.month:
                self.usage["current_cost"]["month"] += round(tokens * tokens_price / 1000, 6)
            else:
                self.usage["current_cost"]["month"] = round(tokens * tokens_price / 1000, 6)
            self.usage["current_cost"]["day"] = round(tokens * tokens_price / 1000, 6)
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
        """Get token amount used on day and month of date

        :param date: date of interest, defaults to date.today()
        :return: total number of tokens used per day and per month
        """        
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
    
    # image usage functions:

    def add_image_request(self, image_size, image_prices="0.016,0.018,0.02"):
        """Add image request to users usage history and update current costs.

        :param image_size: requested image size
        :param image_prices: prices for images of sizes ["256x256", "512x512", "1024x1024"],
                             defaults to [0.016, 0.018, 0.02]
        """        
        sizes = ["256x256", "512x512", "1024x1024"]
        requested_size = sizes.index(image_size)
        image_cost = image_prices[requested_size]

        today = date.today()
        last_update = date.fromisoformat(self.usage["current_cost"]["last_update"])
        # add current cost, update new day
        if today == last_update:
            self.usage["current_cost"]["day"] += image_cost
            self.usage["current_cost"]["month"] += image_cost
        else:
            if today.month == last_update.month:
                self.usage["current_cost"]["month"] += image_cost
            else:
                self.usage["current_cost"]["month"] = image_cost
            self.usage["current_cost"]["day"] = image_cost
            self.usage["current_cost"]["last_update"] = str(today)

        # update usage_history
        if str(today) in self.usage["usage_history"]["number_images"]:
            # add token usage to existing date
            self.usage["usage_history"]["number_images"][str(today)][requested_size] += 1
        else:
            # create new entry for current date
            self.usage["usage_history"]["number_images"][str(today)] = [0, 0, 0]
            self.usage["usage_history"]["number_images"][str(today)][requested_size] += 1
        
        # write updated image number to user file
        with open(self.user_file, "w") as outfile:
            json.dump(self.usage, outfile)

    def get_image_count(self, date=date.today()):
        """Get number of images requested on day and month of date

        :param date: date of interest, defaults to date.today()
        :return: total number of images requested per day and per month
        """      
        if str(date) in self.usage["usage_history"]["number_images"]:
            usage_day = sum(self.usage["usage_history"]["number_images"][str(date)])
        else:
            usage_day = 0
        month = str(date)[:7] # year-month as string
        usage_month = 0
        for date, images in self.usage["usage_history"]["number_images"].items():
            if date.startswith(month):
                usage_month += sum(images)
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
    
    # general functions
    def get_current_cost(self):
        pass
    
    def get_all_stats(self, date=date.today(), token_price=0.002, minute_price=0.006, 
                      image_prices=[0.016, 0.018, 0.02]):
        # TODO: implement
        pass
