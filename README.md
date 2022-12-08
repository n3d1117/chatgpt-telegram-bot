# ChatGPT Telegram Bot
![python-version](https://img.shields.io/badge/python-3.10-blue.svg)
[![playwright-version](https://img.shields.io/badge/revChatGPT-0.0.33.3-green.svg)](https://github.com/acheong08/ChatGPT)
[![license](https://img.shields.io/badge/License-GPL%202.0-brightgreen.svg)](LICENSE)

A [Telegram bot](https://core.telegram.org/bots/api) that integrates with OpenAI's [ChatGPT](https://openai.com/blog/chatgpt/) to provide answers. Ready to use with minimal configuration required. Based on [acheong08/ChatGPT](https://github.com/acheong08/ChatGPT)

## Screenshot
<img width="600" alt="Demo" src="https://user-images.githubusercontent.com/11541888/205654171-80359706-d2ef-4fac-8300-62fe448bfb55.png">

## Prerequisites
- Python 3.10+ and [Pipenv](https://pipenv.readthedocs.io/en/latest/)
- A [Telegram bot](https://core.telegram.org/bots#6-botfather) and its token (see [tutorial](https://core.telegram.org/bots/tutorial#obtain-your-bot-token))
- An [OpenAI](https://openai.com) account (see [configuration](#configuration) section)

## Getting started

### Installing
1. Clone the repository and navigate to the project directory:

```bash
git clone https://github.com/n3d1117/chatgpt-telegram-bot.git
cd chatgpt-telegram-bot
```

2. Create a new virtual environment with Pipenv and install the required dependencies:
```
pipenv install
```

3. Activate the virtual environment:
```
pipenv shell
```

### Configuration
Customize the configuration by copying `.env.example` and renaming it to `.env`, then editing the settings as desired:
```bash
OPENAI_EMAIL="<YOUR_OPENAI_EMAIL>"
OPENAI_PASSWORD="<YOUR_OPENAI_PASSWORD>"
TELEGRAM_BOT_TOKEN="<YOUR_TELEGRAM_BOT_TOKEN>"
```
* `OPENAI_EMAIL,OPENAI_PASSWORD`: Your OpenAI credentials (these are only sent to the OpenAI server to periodically refresh the access token and never shared). You can read more about it [here](https://github.com/acheong08/ChatGPT)
* `TELEGRAM_BOT_TOKEN`: Your Telegram bot's token, obtained using [BotFather](http://t.me/botfather) (see [tutorial](https://core.telegram.org/bots/tutorial#obtain-your-bot-token))

Additional optional (but recommended) configuration values:
```bash
ALLOWED_TELEGRAM_USER_IDS="<USER_ID_1>,<USER_ID_2>,..." # Defaults to "*"
PROXY="<HTTP/HTTPS_PROXY>" # E.g. "http://localhost:8080", defaults to none
DEBUG=false # Defaults to true
```
* `ALLOWED_TELEGRAM_USER_IDS`: A comma-separated list of Telegram user IDs that are allowed to interact with the bot (use [getidsbot](https://t.me/getidsbot) to find your user ID). **Important**: by default, *everyone* is allowed (`*`)
* `PROXY`: Proxy to be used when authenticating with OpenAI
* `DEBUG`: Enable debug logging for the [revChatGpt](https://github.com/acheong08/ChatGPT) package

### Run
Use the following command to start the bot:
```
python main.py
```

## Credits
- [ChatGPT](https://chat.openai.com/chat) from [OpenAI](https://openai.com)
- [acheong08/ChatGPT](https://github.com/acheong08/ChatGPT) for reverse engineering ChatGPT APIs
- [python-telegram-bot](https://python-telegram-bot.org)

## Disclaimer
This is a personal project and is not affiliated with OpenAI in any way.

## License
This project is released under the terms of the GPL 2.0 license. For more information, see the [LICENSE](LICENSE) file included in the repository.
