# ChatGPT Telegram Bot
![python-version](https://img.shields.io/badge/python-3.10-blue.svg)
[![openai-version](https://img.shields.io/badge/openai-0.27.0-green.svg)](https://openai.com/)
[![license](https://img.shields.io/badge/License-GPL%202.0-brightgreen.svg)](LICENSE)

A [Telegram bot](https://core.telegram.org/bots/api) that integrates with OpenAI's _official_ [ChatGPT](https://openai.com/blog/chatgpt/) APIs to provide answers. Ready to use with minimal configuration required.

## Screenshot
<img width="600" alt="Demo" src="https://user-images.githubusercontent.com/11541888/205654171-80359706-d2ef-4fac-8300-62fe448bfb55.png">

## Features
- [x] Reply to specific messages
- [x] Support markdown in answers
- [x] Reset conversation with the `/reset` command
- [x] Typing indicator while generating a response
- [x] Access can be restricted by specifying a list of allowed users
- [x] Docker support
- [x] (NEW!) Customizable initial assistant prompt

## Coming soon
- [ ] Customizable temperature
- [ ] Better handling of rate limiting errors
- [ ] See remaining tokens and current usage
- [ ] Multi-chat support
- [ ] Image generation using DALL·E APIs

## Additional Features - help needed!
- [ ] Group chat support

PRs are always welcome!

## Prerequisites
- Python 3.10+ and [Pipenv](https://pipenv.readthedocs.io/en/latest/)
- A [Telegram bot](https://core.telegram.org/bots#6-botfather) and its token (see [tutorial](https://core.telegram.org/bots/tutorial#obtain-your-bot-token))
- An [OpenAI](https://openai.com) account (see [configuration](#configuration) section)

## Getting started

### Configuration
Customize the configuration by copying `.env.example` and renaming it to `.env`, then editing the settings as desired:
```bash
OPENAI_API_KEY="<YOUR_OPENAI_API_KEY>"
TELEGRAM_BOT_TOKEN="<YOUR_TELEGRAM_BOT_TOKEN>"
```
* `OPENAI_API_KEY`: Your OpenAI API key, get if from [here](https://platform.openai.com/account/api-keys)
* `TELEGRAM_BOT_TOKEN`: Your Telegram bot's token, obtained using [BotFather](http://t.me/botfather) (see [tutorial](https://core.telegram.org/bots/tutorial#obtain-your-bot-token))

Additional optional (but recommended) configuration values:
```bash
ALLOWED_TELEGRAM_USER_IDS="<USER_ID_1>,<USER_ID_2>,..." # Defaults to "*"
ASSISTANT_PROMPT="..." # Defaults to "You are a helpful assistant."
```
* `ALLOWED_TELEGRAM_USER_IDS`: A comma-separated list of Telegram user IDs that are allowed to interact with the bot (use [getidsbot](https://t.me/getidsbot) to find your user ID). **Important**: by default, *everyone* is allowed (`*`)
* `ASSISTANT_PROMPT`: A system message that controls the behavior of the assistant. See [the docs](https://platform.openai.com/docs/guides/chat/introduction) for more details

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

## Disclaimer
This is a personal project and is not affiliated with OpenAI in any way.

## License
This project is released under the terms of the GPL 2.0 license. For more information, see the [LICENSE](LICENSE) file included in the repository.
