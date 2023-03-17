# ChatGPT Telegram Bot
![python-version](https://img.shields.io/badge/python-3.10-blue.svg)
[![openai-version](https://img.shields.io/badge/openai-0.27.0-green.svg)](https://openai.com/)
[![license](https://img.shields.io/badge/License-GPL%202.0-brightgreen.svg)](LICENSE)

A [Telegram bot](https://core.telegram.org/bots/api) that integrates with OpenAI's _official_ [ChatGPT](https://openai.com/blog/chatgpt/) APIs to provide answers. Ready to use with minimal configuration required.

## Screenshots
![demo](https://user-images.githubusercontent.com/11541888/225114786-0d639854-b3e1-4214-b49a-e51ce8c40387.png)

## Features
- [x] Support markdown in answers
- [x] Reset conversation with the `/reset` command
- [x] Typing indicator while generating a response
- [x] Access can be restricted by specifying a list of allowed users
- [x] Docker and Proxy support
- [x] (NEW!) Image generation using DALL·E via the `/image` command
- [x] (NEW!) Transcribe audio and video messages using Whisper (may require [ffmpeg](https://ffmpeg.org))
- [x] (NEW!) Automatic conversation summary to avoid excessive token usage (fixes [#34](https://github.com/n3d1117/chatgpt-telegram-bot/issues/34))
- [x] (NEW!) Group chat support with inline queries 
  - To use this feature, enable inline queries for your bot in BotFather via the `/setinline` [command](https://core.telegram.org/bots/inline)
- [x] (NEW!) Track token usage per user - by [@AlexHTW](https://github.com/AlexHTW)
- [x] (NEW!) Get personal token usage statistics and cost per day/month via the `/stats` command - by [@AlexHTW](https://github.com/AlexHTW)
- [x] (NEW!) User budgets and guest budgets - by [@AlexHTW](https://github.com/AlexHTW)

## Additional features - help needed!
- [ ] Add stream support ([#43](https://github.com/n3d1117/chatgpt-telegram-bot/issues/43))
- [ ] Handle responses longer than telegram message limit ([#44](https://github.com/n3d1117/chatgpt-telegram-bot/issues/44))

PRs are always welcome!

## Prerequisites
- Python 3.10+ and [Pipenv](https://pipenv.readthedocs.io/en/latest/)
- A [Telegram bot](https://core.telegram.org/bots#6-botfather) and its token (see [tutorial](https://core.telegram.org/bots/tutorial#obtain-your-bot-token))
- An [OpenAI](https://openai.com) account (see [configuration](#configuration) section)

## Getting started

### Configuration
Customize the configuration by copying `.env.example` and renaming it to `.env`, then editing the parameters as desired:
```bash
OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"

# Optional parameters
ALLOWED_TELEGRAM_USER_IDS="USER_ID_1,USER_ID_2,..." # Defaults to "*" (everyone)
MONTHLY_USER_BUDGETS="BUDGET_USER_ID_1,BUDGET_USER_ID_2,..." # Defaults to "*" (no restrictions)
MONTHLY_GUEST_BUDGET="20.0" # Defaults to 100.0
PROXY="YOUR_PROXY" # e.g. "http://localhost:8080", defaults to none
OPENAI_MODEL="gpt-3.5-turbo" # Defaults to gpt-3.5-turbo
ASSISTANT_PROMPT="Custom prompt" # Defaults to "You are a helpful assistant."
SHOW_USAGE=true # Defaults to false
MAX_TOKENS=2000 # Defaults to 1200
MAX_HISTORY_SIZE=15 # Defaults to 10
MAX_CONVERSATION_AGE_MINUTES=120 # Defaults to 180 (3h)
VOICE_REPLY_WITH_TRANSCRIPT_ONLY=false # Defaults to true
N_CHOICES=1 # Defaults to 1
TEMPERATURE=1.0 # Defaults to 1.0
PRESENCE_PENALTY=0 # Defaults to 0
FREQUENCY_PENALTY=0 # Defaults to 0
IMAGE_SIZE="256x256" # Defaults to 512x512
GROUP_TRIGGER_KEYWORD="@bot" # Defaults to "" (no keyword required)
IGNORE_GROUP_TRANSCRIPTIONS=true # Whether transcriptions should be ignored in group chats. Defaults to true
TOKEN_PRICE=0.002 # Defaults to 0.002, current price: https://openai.com/pricing
IMAGE_PRICES="0.016,0.018,0.02" # Defaults to OpenAI Dall-E pricing for sizes 256x256,512x512,1024x1024
TRANSCRIPTION_PRICE=0.006 # Defaults to minute price of OpenAI Whisper of 0.006
```
* `OPENAI_API_KEY`: Your OpenAI API key, you can get it from [here](https://platform.openai.com/account/api-keys)
* `TELEGRAM_BOT_TOKEN`: Your Telegram bot's token, obtained using [BotFather](http://t.me/botfather) (see [tutorial](https://core.telegram.org/bots/tutorial#obtain-your-bot-token))
* `ALLOWED_TELEGRAM_USER_IDS`: A comma-separated list of Telegram user IDs that are allowed to interact with the bot (use [getidsbot](https://t.me/getidsbot) to find your user ID). **Note**: by default, *everyone* is allowed (`*`)
* `MONTHLY_USER_BUDGETS`: A comma-separated list of $-amounts per user from list `ALLOWED_TELEGRAM_USER_IDS` to set custom usage limit of OpenAI API costs for each. **Note**: by default, *no limits* for anyone (`*`)
* `MONTHLY_GUEST_BUDGET`: $-amount as usage limit for all guest users. Guest users are users in group chats that are not in the `ALLOWED_TELEGRAM_USER_IDS` list. Value is ignored if no usage limits are set in user budgets (`MONTHLY_USER_BUDGETS`="*")
* `PROXY`: Proxy to be used for OpenAI and Telegram bot
* `OPENAI_MODEL`: Define which OpenAI model to use (default is `gpt-3.5-turbo`)
* `ASSISTANT_PROMPT`: A system message that sets the tone and controls the behavior of the assistant
* `SHOW_USAGE`: Whether to show OpenAI token usage information after each response
* `MAX_TOKENS`: Upper bound on how many tokens the ChatGPT API will return
* `MAX_HISTORY_SIZE`: Max number of messages to keep in memory, after which the conversation will be summarised to avoid excessive token usage ([#34](https://github.com/n3d1117/chatgpt-telegram-bot/issues/34))
* `MAX_CONVERSATION_AGE_MINUTES`: Maximum number of minutes a conversation should live, after which the conversation will be reset to avoid excessive token usage
* `VOICE_REPLY_WITH_TRANSCRIPT_ONLY`: Whether to answer to voice messages with the transcript only or with a ChatGPT response of the transcript ([#38](https://github.com/n3d1117/chatgpt-telegram-bot/issues/38))
* `N_CHOICES`: Number of answers to generate for each input message
* `TEMPERATURE`: Number between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic
* `PRESENCE_PENALTY`: Number between -2.0 and 2.0. Positive values penalize new tokens based on whether they appear in the text so far, increasing the model's likelihood to talk about new topics
* `FREQUENCY_PENALTY`: Number between -2.0 and 2.0. Positive values penalize new tokens based on their existing frequency in the text so far, decreasing the model's likelihood to repeat the same line verbatim
* `IMAGE_SIZE`: The DALL·E generated image size. Allowed values: "256x256", "512x512", or "1024x1024"
* `GROUP_TRIGGER_KEYWORD`: If set, the bot will only respond to messages that start with this keyword. This is useful for bots added to groups with privacy mode disabled. **Note**: by default, *no keyword* is required (`""`)
* `IGNORE_GROUP_TRANSCRIPTIONS`: If set to true, the bot will not process transcriptions in group chats
* `TOKEN_PRICE`: USD-price per 1000 tokens for cost information in usage statistics. Defaults to [OpenAI price](https://openai.com/pricing) for gpt-3.5-turbo
* `IMAGE_PRICES`: A comma-separated list with 3 elements of prices for the different image sizes 256x256, 512x512 and 1024x1024. Defaults to [OpenAI prices](https://openai.com/pricing) for Dall-E.
* `TRANSCRIPTION_PRICE`: USD-price for one minute of audio transcription. Defaults to [OpenAI price](https://openai.com/pricing) for Whisper

Check out the [official API reference](https://platform.openai.com/docs/api-reference/chat) for more details.

### Installing
1. Clone the repository and navigate to the project directory:

```bash
git clone https://github.com/n3d1117/chatgpt-telegram-bot.git
cd chatgpt-telegram-bot
```

#### From Source
2. Create a new virtual environment with Pipenv and install the required dependencies:
```
pipenv install
```

3. Activate the virtual environment:
```
pipenv shell
```

4. Use the following command to start the bot:
```
python main.py
```

#### Using Docker Compose

2. Run the following command to build and run the Docker image:
```bash
docker-compose up
```

## Credits
- [ChatGPT](https://chat.openai.com/chat) from [OpenAI](https://openai.com)
- [python-telegram-bot](https://python-telegram-bot.org)
- [jiaaro/pydub](https://github.com/jiaaro/pydub)

## Disclaimer
This is a personal project and is not affiliated with OpenAI in any way.

## License
This project is released under the terms of the GPL 2.0 license. For more information, see the [LICENSE](LICENSE) file included in the repository.
