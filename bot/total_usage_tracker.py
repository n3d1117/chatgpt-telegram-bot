import os.path
import pathlib
import json
from datetime import date, timedelta
import time
from openai_helper import OpenAIHelper, localized_text

MAX_REQUESTS_PER_MINUTE = 5 # max requests to OpenAI API per minute

class TotalUsageTracker:
    """
    TotalUsageTracker class
    Enables tracking of daily/monthly total usage.
    Usage per date is stored in /usage_logs/total_usage.json file.
    JSON example:
    {
        "2023-07-01": {
            "data": [
                {"n_requests": 24, "n_context": 24, "n_context_tokens_total": 7684, "n_generated": 24, "n_generated_tokens_total": 1538, "snapshot_id": "gpt-3.5-turbo-0613", "operation": "completion"}
            ],
            "ft_data": [],
            "dalle_api_data": [
                {"num_images": 1, "num_requests": 1, "image_size": "512x512", "operation": "generations"}
            ],
            "whisper_api_data": [
                {"num_seconds": 3, "num_requests": 1, "model_id": "whisper-1"}
            ],
            "current_usage_usd": 0.2
        },
    }
    """

    def __init__(self, openai: OpenAIHelper, logs_dir="usage_logs"):
        """
        Initializes TotalUsageTracker
        :param openai: OpenAIHelper instance
        :param logs_dir: path to directory of usage logs, defaults to "usage_logs"
        """
        self.openai = openai
        self.logs_dir = logs_dir
        self.usage_file = f"{logs_dir}/total_usage.json"

        if os.path.isfile(self.usage_file):
            with open(self.usage_file, "r") as file:
                self.usage = json.load(file)
        else:
            # ensure directory exists
            pathlib.Path(logs_dir).mkdir(exist_ok=True)
            # create new dictionary
            self.usage = {}

    def add_usage_on_date(self, day):
        """Add usage on a specific date to usage history.
        :param day: date of usage
        """
        usage = self.openai.get_usage(day)

        # example usage: {"object": "list", "data": [
        #  {"aggregation_timestamp": <timestamp>, "n_requests": 1, "operation": "completion", "snapshot_id": "gpt-3.5-turbo-0613", "n_context": 1, "n_context_tokens_total": 74, "n_generated": 1, "n_generated_tokens_total": 35},
        #  {"aggregation_timestamp": <timestamp>, "n_requests": 1, "operation": "completion", "snapshot_id": "gpt-3.5-turbo-0613", "n_context": 1, "n_context_tokens_total": 28, "n_generated": 1, "n_generated_tokens_total": 188}
        # ],"ft_data": [], "dalle_api_data": [
        # {"timestamp": <timestamp>, "num_images": 1, "num_requests": 1, "image_size": "512x512", "operation": "generations"}
        # ], "whisper_api_data": [
        # {"timestamp": <timestamp>, "num_seconds": 3, "num_requests": 1, "model_id": "whisper-1"}
        #], "current_usage_usd": 0.0},

        # minimize the usage data length
        usage.pop("object")
        self.pack_usage_data(usage, "data", ("snapshot_id", "operation"),
            ("n_requests", "n_context", "n_context_tokens_total", "n_generated", "n_generated_tokens_total"))
        self.pack_usage_data(usage, "dalle_api_data", ("image_size", "operation"), ("num_images", "num_requests"))
        self.pack_usage_data(usage, "whisper_api_data", ("model_id",), ("num_seconds", "num_requests"))

        self.usage[str(day)] = usage

        with open(self.usage_file, "w") as outfile:
            json.dump(self.usage, outfile)

        return usage

    def pack_usage_data(self, usage, data_key, index_keys, aggregated_keys):
        """Pack usage data per operation and snapshot_id
        :param usage: usage data
        :param data_key: key of usage data to pack
        :param keys: keys to pack
        :return: packed usage data
        """
        h = {}
        for raw in usage[data_key]:
            index = tuple([raw[key] for key in index_keys])
            total = h.get(index) or dict.fromkeys(aggregated_keys, 0)
            for key in aggregated_keys: total[key] += raw[key]
            for key in index_keys: total[key] = raw[key]
            h[index] = total
        usage[data_key] = list(h.values())


    def get_month_usage(self):
        """Get total usd usage per moth
        If it's not the current day, it looks for the date in usage history.
        If it's not existing or it's the current date, it requests the usage from the openai API.
        :return: total usd
        """
        today = date.today()
        day = date(today.year, today.month, 1)

        # counter to minimize fake delays
        requests_count = today.day

        # cycle through all billing days from first day to last_day
        total_usage_usd = 0
        while day <= today:
            data = self.usage.get(str(day))
            data_absent = data is None
            if data_absent or (day == today):
                data = self.add_usage_on_date(day)
            else:
                requests_count -= 1
            total_usage_usd += data["current_usage_usd"]
            # wait if the request was made for a day in the past and requests count below the limit
            if data_absent and (day != today) and (requests_count > MAX_REQUESTS_PER_MINUTE):
                print(f"Usage data for {day} was received. Waiting for next request...")
                time.sleep(60 / MAX_REQUESTS_PER_MINUTE + 1)
            # increment day
            day += timedelta(days=1)

        return total_usage_usd
