# ChatGPT Telegram Bot
![python-version](https://img.shields.io/badge/python-3.9-blue.svg)
[![openai-version](https://img.shields.io/badge/openai-0.27.2-orange.svg)](https://openai.com/)
[![license](https://img.shields.io/badge/License-GPL%202.0-brightgreen.svg)](LICENSE)
[![Publish Docker image](https://github.com/n3d1117/chatgpt-telegram-bot/actions/workflows/publish.yaml/badge.svg)](https://github.com/n3d1117/chatgpt-telegram-bot/actions/workflows/publish.yaml)

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
- [x] (NEW!) Stream support
- [x] (NEW!) GPT-4 support
  - If you have access to the GPT-4 API, simply change the `OPENAI_MODEL` parameter to `gpt-4`

## Additional features - help needed!
- [ ] Add session persistence ([#70](https://github.com/n3d1117/chatgpt-telegram-bot/issues/70), [#71](https://github.com/n3d1117/chatgpt-telegram-bot/issues/71))

PRs are always welcome!

## Prerequisites
- Python 3.9+
- A [Telegram bot](https://core.telegram.org/bots#6-botfather) and its token (see [tutorial](https://core.telegram.org/bots/tutorial#obtain-your-bot-token))
- An [OpenAI](https://openai.com) account (see [configuration](#configuration) section)

## Getting started

### Configuration
Customize the configuration by copying `.env.example` and renaming it to `.env`, then editing the required parameters as desired:

| Parameter                   | Description                                                                                                                                                                                                                   |
|-----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `OPENAI_API_KEY`            | Your OpenAI API key, you can get it from [here](https://platform.openai.com/account/api-keys)                                                                                                                                 |
| `TELEGRAM_BOT_TOKEN`        | Your Telegram bot's token, obtained using [BotFather](http://t.me/botfather) (see [tutorial](https://core.telegram.org/bots/tutorial#obtain-your-bot-token))                                                                  |
| `ADMIN_USER_IDS`            | Telegram user IDs of admins. These users have access to special admin commands, information and no budget restrictions. Admin IDs don't have to be added to `ALLOWED_TELEGRAM_USER_IDS`. **Note**: by default, no admin ('-') |
| `ALLOWED_TELEGRAM_USER_IDS` | A comma-separated list of Telegram user IDs that are allowed to interact with the bot (use [getidsbot](https://t.me/getidsbot) to find your user ID). **Note**: by default, *everyone* is allowed (`*`)                       |

### Optional configuration
| Parameter                          | Description                                                                                                                                                                                                                      | Default value                  |
|------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------|
| `MONTHLY_USER_BUDGETS`             | A comma-separated list of $-amounts per user from list `ALLOWED_TELEGRAM_USER_IDS` to set custom usage limit of OpenAI API costs for each.  **Note**: by default, *no limits* for anyone (`*`)                                   | `*`                            |
| `MONTHLY_GUEST_BUDGET`             | $-amount as usage limit for all guest users. Guest users are users in group chats that are not in the `ALLOWED_TELEGRAM_USER_IDS` list. Value is ignored if no usage limits are set in user budgets (`MONTHLY_USER_BUDGETS`="*") | `100.0`                        |
| `PROXY`                            | Proxy to be used for OpenAI and Telegram bot (e.g. `http://localhost:8080`)                                                                                                                                                      | -                              |
| `OPENAI_MODEL`                     | The OpenAI model to use for generating responses                                                                                                                                                                                 | `gpt-3.5-turbo`                |
| `ASSISTANT_PROMPT`                 | A system message that sets the tone and controls the behavior of the assistant                                                                                                                                                   | `You are a helpful assistant.` |
| `SHOW_USAGE`                       | Whether to show OpenAI token usage information after each response                                                                                                                                                               | false                          |
| `STREAM`                           | Whether to stream responses. **Note**: incompatible, if enabled, with `N_CHOICES` higher than 1                                                                                                                                  | true                           |
| `MAX_TOKENS`                       | Upper bound on how many tokens the ChatGPT API will return                                                                                                                                                                       | 1200                           |
| `MAX_HISTORY_SIZE`                 | Max number of messages to keep in memory, after which the conversation will be summarised to avoid excessive token usage                                                                                                         | 15                             |
| `MAX_CONVERSATION_AGE_MINUTES`     | Maximum number of minutes a conversation should live since the last message, after which the conversation will be reset                                                                                                          | 180                            |
| `VOICE_REPLY_WITH_TRANSCRIPT_ONLY` | Whether to answer to voice messages with the transcript only or with a ChatGPT response of the transcript                                                                                                                        | true                           |
| `N_CHOICES`                        | Number of answers to generate for each input message. **Note**: setting this to a number higher than 1 will not work properly if `STREAM` is enabled                                                                             | 1                              |
| `TEMPERATURE`                      | Number between 0 and 2. Higher values will make the output more random                                                                                                                                                           | 1.0                            |
| `PRESENCE_PENALTY`                 | Number between -2.0 and 2.0. Positive values penalize new tokens based on whether they appear in the text so far                                                                                                                 | 0                              |
| `FREQUENCY_PENALTY`                | Number between -2.0 and 2.0. Positive values penalize new tokens based on their existing frequency in the text so far                                                                                                            | 0                              |
| `IMAGE_SIZE`                       | The DALL·E generated image size. Allowed values: "256x256", "512x512" or "1024x1024"                                                                                                                                             | "512x512"                      |
| `GROUP_TRIGGER_KEYWORD`            | If set, the bot in group chats will only respond to messages that start with this keyword                                                                                                                                        | ""                             |
| `IGNORE_GROUP_TRANSCRIPTIONS`      | If set to true, the bot will not process transcriptions in group chats                                                                                                                                                           | true                           |
| `TOKEN_PRICE`                      | $-price per 1000 tokens used to compute cost information in usage statistics (https://openai.com/pricing)                                                                                                                        | 0.002                          |
| `IMAGE_PRICES`                     | A comma-separated list with 3 elements of prices for the different image sizes: "256x256", "512x512" and "1024x1024"                                                                                                             | "0.016,0.018,0.02"             |
| `TRANSCRIPTION_PRICE`              | USD-price for one minute of audio transcription                                                                                                                                                                                  | 0.002                          |

Check out the [official API reference](https://platform.openai.com/docs/api-reference/chat) for more details.

### Installing
Clone the repository and navigate to the project directory:

```shell
git clone https://github.com/n3d1117/chatgpt-telegram-bot.git
cd chatgpt-telegram-bot
```

#### From Source
1. Create a virtual environment:
```shell
python -m venv venv
```

2. Activate the virtual environment:
```shell
# For Linux or macOS:
source venv/bin/activate

# For Windows:
venv\Scripts\activate
```

3. Install the dependencies using `requirements.txt` file:
```shell
pip install -r requirements.txt
```

4. Use the following command to start the bot:
```
python bot/main.py
```

#### Using Docker Compose

Run the following command to build and run the Docker image:
```shell
docker compose up
```

#### Ready-to-use Docker images
You can also use the Docker image from [Docker Hub](https://hub.docker.com/r/n3d1117/chatgpt-telegram-bot):
```shell
docker pull n3d1117/chatgpt-telegram-bot:latest
```

or using the [GitHub Container Registry](https://github.com/n3d1117/chatgpt-telegram-bot/pkgs/container/chatgpt-telegram-bot/):

```shell
docker pull ghcr.io/n3d1117/chatgpt-telegram-bot:latest
```

## Credits
- [ChatGPT](https://chat.openai.com/chat) from [OpenAI](https://openai.com)
- [python-telegram-bot](https://python-telegram-bot.org)
- [jiaaro/pydub](https://github.com/jiaaro/pydub)

## Disclaimer
This is a personal project and is not affiliated with OpenAI in any way.

## License
This project is released under the terms of the GPL 2.0 license. For more information, see the [LICENSE](LICENSE) file included in the repository.
