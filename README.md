# ChatGPT Telegram Bot
![python-version](https://img.shields.io/badge/python-3.10-blue.svg)
![playwright-version](https://img.shields.io/badge/playwright-1.28.0-green.svg)
[![license](https://img.shields.io/badge/License-GPL%202.0-brightgreen.svg)](LICENSE)

A [Telegram bot](https://core.telegram.org/bots/api) that integrates with OpenAI's [ChatGPT](https://openai.com/blog/chatgpt/) to provide answers. Ready to use with minimal configuration required.

## Screenshot
<img width="600" alt="Demo" src="https://user-images.githubusercontent.com/11541888/205508077-c6fa9c30-242e-4605-81a6-1049ca0060f3.png">

## Prerequisites
- [Pipenv](https://pipenv.readthedocs.io/en/latest/)
- A [Telegram bot](https://core.telegram.org/bots#6-botfather) and its token
- Your [OpenAI](https://openai.com) session token (see [configuration](#configuration) section)

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
Customize the configuration by copying `config.json.example` and renaming it to `config.json`, then editing the settings as desired.
```
{
    "openai_session_token": "<YOUR_OPENAI_SESSION_TOKEN>",
    "telegram_bot_token": "<YOUR_TELEGRAM_BOT_TOKEN>"
}
```
You'll need to provide:
1. Your OpenAI session token (this is only sent to the OpenAI server to periodically refresh the access token and never shared), which expires after 1 month
  - You can find this token in your browser's cookies (named `__Secure-next-auth.session-token`) after logging in to https://chat.openai.com/chat
  - Alternatively, run the following code:
    ```shell
    pip install playwright
    python openai_extract_session_token.py <YOUR_OPENAI_EMAIL> <YOUR_OPENAI_PASSWORD>
    ```
2. Your Telegram bot's token, obtained using [BotFather](http://t.me/botfather)

### Run the project
Use the following command to run the project:
```
python main.py
```

## Credits
- [ChatGPT](https://chat.openai.com/chat) from [OpenAI](https://openai.com)
- [acheong08/ChatGPT](https://github.com/acheong08/ChatGPT) for reverse engineering ChatGPT APIs
- [python-telegram-bot](https://python-telegram-bot.org)

## License
This project is released under the terms of the GPL 2.0 license. For more information, see the [LICENSE](LICENSE) file included in the repository.
