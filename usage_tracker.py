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
    JSON schema:
        {"chat_tokens":{year-month:{day: total_tokens_used}, ...},
        {"audio_seconds":{year-month:{day: total_seconds_transcribed}, ...},
        {"image_count":{year-month:{day: [nr_images_small, nr_images_medium, nr_images_large]}, ...}}
    """

    def __init__(self, user_id, logs_dir="usage_logs"):
        """
        Initializes UsageTracker for a user with current date. 
        Loads usage data from usage log file.
        :param user_id: Telegram ID of the user
        :param logs_dir: path to directory of usage logs, default "usage_logs"
        """
        self.user_id = user_id
        self.logs_dir = logs_dir
        # path to usage file of given user
        self.user_file = f"{logs_dir}/{user_id}.json"
        # current year-month as string
        self.current_month = year_month(date.today())
        # current day as string, no leading zero
        self.current_day = str(date.today().day)

        if os.path.isfile(self.user_file):
            with open(self.user_file, "r") as file:
                self.usage = json.load(file)
        else:
            # ensure directory exists 
            pathlib.Path(logs_dir).mkdir(exist_ok=True)
            # create empty dictionary for this user
            self.usage = {}

    # token usage functions:
    
    def add_chat_tokens(self, tokens):
        """
        Adds used tokens from a request to a users usage .
        :param tokens: total tokens used in last request
        """
        if "chat_tokens" in self.usage:
            if self.current_month in self.usage["chat_tokens"]:
                if self.current_day in self.usage["chat_tokens"][self.current_month]:
                    # add token usage to existing month and day
                    self.usage["chat_tokens"][self.current_month][self.current_day] += tokens
                else:
                    # create new entry for current day
                    self.usage["chat_tokens"][self.current_month][self.current_day] = tokens
            else:
                # create new entry for current month and day
                self.usage["chat_tokens"][self.current_month] = {self.current_day: tokens}
        else: # add chat_tokens key and token usage for current month and day
            self.usage["chat_tokens"] = {self.current_month: {self.current_day: tokens}}
        
        # write updated token usage to user file
        with open(self.user_file, "w") as outfile:
            json.dump(self.usage, outfile)

    def get_token_usage(self, date=date.today()):
        """
        Gets tokens used per day and sums tokens per month of given date.
        Returns both values.
        :param date: datetime.date object, default today
        """
        # year-month as string
        month = year_month(date)
        # day as string, no leading zero
        day = str(date.day)
        usage_day = self.usage["chat_tokens"][month][day]
        usage_month = sum(list(self.usage["chat_tokens"][month].values()))
        return usage_day, usage_month

    @staticmethod
    def cost_tokens(tokens, token_price=0.002):
        # cost of token amount in USD
        # current price gpt-3.5-turbo: $0.002/1000 tokens
        price_per_token = token_price*0.001
        return tokens * price_per_token
    
    def get_token_count_and_cost(self, date=date.today(), token_price=0.002):
        """
        Gets total cost of tokens used per day and per month of given date.
        :param date: datetime.date object, default today
        :param token_price: price of 1000 tokens
        :returns: 4 values (token count day, token count month, token cost day, 
                  token cost month)
        """
        tokens_day, tokens_month = self.get_token_usage(date)
        cost_day = self.cost_tokens(tokens_day, token_price)
        cost_month = self.cost_tokens(tokens_month, token_price)
        return tokens_day, tokens_month, cost_day, cost_month 

    # transcription usage functions:

    def add_audio_seconds(self, seconds):
        # TODO: implement
        pass

    def get_transcription_usage(self, date=date.today()):
        # TODO: implement
        pass

    @staticmethod
    def cost_tokens(seconds, minute_price=0.006):
        # cost of audio seconds transcribed, amount in USD
        # current price Whisper: $0.002/1000 tokens
        second_price = minute_price/60
        return seconds * second_price
    
    def get_audio_seconds_and_cost(self, date=date.today(), minute_price=0.006):
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
    def get_all_stats(self, date=date.today(), token_price=0.002, minute_price=0.006, 
                      image_prices=[0.016, 0.018, 0.02]):
        # TODO: implement
        pass

    def summarize_past_daily_usage(self):
        # TODO: implement
        pass
