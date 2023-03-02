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
- [x] (NEW!) Support multiple answers!
- [x] (NEW!) Customizable model parameters (see [configuration](#configuration) section)
- [x] (NEW!) See token usage after each answer

## Coming soon
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
ALLOWED_TELEGRAM_USER_IDS="<USER_ID_1>,<USER_ID_2>,..." # Defaults to "*" (everyone)
SHOW_USAGE=false
```
* `OPENAI_API_KEY`: Your OpenAI API key, get if from [here](https://platform.openai.com/account/api-keys)
* `TELEGRAM_BOT_TOKEN`: Your Telegram bot's token, obtained using [BotFather](http://t.me/botfather) (see [tutorial](https://core.telegram.org/bots/tutorial#obtain-your-bot-token))
* `ALLOWED_TELEGRAM_USER_IDS`: A comma-separated list of Telegram user IDs that are allowed to interact with the bot (use [getidsbot](https://t.me/getidsbot) to find your user ID). **Important**: by default, *everyone* is allowed (`*`)
* `SHOW_USAGE`: Whether to show OpenAI token usage information after each response. Optional, defaults to `false`

Additional optional model parameters can be configured from the `main.py` file:
```python
{
    # 'gpt-3.5-turbo' or 'gpt-3.5-turbo-0301'
    'model': 'gpt-3.5-turbo',
    
    # An initial system message that sets the tone and controls the behavior of the assistant.
    'assistant_prompt': 'You are a helpful assistant.',
    
    # Number between 0 and 2. Higher values like 0.8 will make the output more random,
    # while lower values like 0.2 will make it more focused and deterministic. Defaults to 1
    'temperature': 1,
    
    # How many answers to generate for each input message. Defaults to 1
    'n_choices': 1,
    
    # The maximum number of tokens allowed for the generated answer. Defaults to 4096 minus prompt tokens
    'max_tokens': 1200,
    
    # Number between -2.0 and 2.0. Positive values penalize new tokens based on whether
    # they appear in the text so far, increasing the model's likelihood to talk about new topics. Defaults to 0
    'presence_penalty': 0,
    
    # Number between -2.0 and 2.0. Positive values penalize new tokens based on their existing
    # frequency in the text so far, decreasing the model's likelihood to repeat the same line verbatim. Defaults to 0
    'frequency_penalty': 0
}
```
See the [official API reference](https://platform.openai.com/docs/api-reference/chat) for more details.

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
