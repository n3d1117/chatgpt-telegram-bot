import datetime
import logging
from typing import Union

import tiktoken

import openai


class OpenAIHelper:
    """
    ChatGPT helper class.
    """

    def __init__(self, config: dict):
        """
        Initializes the OpenAI helper class with the given configuration.
        :param config: A dictionary containing the GPT configuration
        """
        openai.api_key = config['api_key']
        openai.proxy = config['proxy']
        self.config = config
        self.conversations: dict[int: list] = {}  # {chat_id: history}
        self.last_updated: dict[int: datetime] = {}  # {chat_id: last_update_timestamp}

    async def get_chat_response(self, chat_id: int, query: str) -> Union[tuple[str, str], str]:
        """
        Gets a response from the GPT-3 model.
        :param chat_id: The chat ID
        :param query: The query to send to the model
        :return: The answer from the model and the number of tokens used, or an error message
        """
        try:
            if chat_id not in self.conversations or self.__max_age_reached(chat_id):
                self.reset_chat_history(chat_id)

            self.last_updated[chat_id] = datetime.datetime.now()

            self.__add_to_history(chat_id, role="user", content=query)

            # Summarize the chat history if it's too long to avoid excessive token usage
            token_count = self.__count_tokens(self.conversations[chat_id])
            exceeded_max_tokens = token_count + self.config['max_tokens'] > self.__max_model_tokens()
            exceeded_max_history_size = len(self.conversations[chat_id]) > self.config['max_history_size']

            if exceeded_max_tokens or exceeded_max_history_size:
                logging.info(f'Chat history for chat ID {chat_id} is too long. Summarising...')
                try:
                    summary = await self.__summarise(self.conversations[chat_id][:-1])
                    logging.debug(f'Summary: {summary}')
                    self.reset_chat_history(chat_id)
                    self.__add_to_history(chat_id, role="assistant", content=summary)
                    self.__add_to_history(chat_id, role="user", content=query)
                except Exception as e:
                    logging.warning(f'Error while summarising chat history: {str(e)}. Popping elements instead...')
                    self.conversations[chat_id] = self.conversations[chat_id][-self.config['max_history_size']:]

            response = await openai.ChatCompletion.acreate(
                model=self.config['model'],
                messages=self.conversations[chat_id],
                temperature=self.config['temperature'],
                n=self.config['n_choices'],
                max_tokens=self.config['max_tokens'],
                presence_penalty=self.config['presence_penalty'],
                frequency_penalty=self.config['frequency_penalty'],
            )

            if len(response.choices) > 0:
                answer = ''

                if len(response.choices) > 1 and self.config['n_choices'] > 1:
                    for index, choice in enumerate(response.choices):
                        content = choice['message']['content'].strip()
                        if index == 0:
                            self.__add_to_history(chat_id, role="assistant", content=content)
                        answer += f'{index+1}\u20e3\n'
                        answer += content
                        answer += '\n\n'
                else:
                    answer = response.choices[0]['message']['content'].strip()
                    self.__add_to_history(chat_id, role="assistant", content=answer)

                if self.config['show_usage']:
                    answer += "\n\n---\n" \
                              f"💰 Tokens used: {str(response.usage['total_tokens'])}" \
                              f" ({str(response.usage['prompt_tokens'])} prompt," \
                              f" {str(response.usage['completion_tokens'])} completion)"

                return answer, response.usage['total_tokens']

            logging.error('No response from GPT-3')
            return "⚠️ _An error has occurred_ ⚠️\nPlease try again in a while."

        except openai.error.RateLimitError as e:
            logging.exception(e)
            return f"⚠️ _OpenAI Rate Limit exceeded_ ⚠️\n{str(e)}"

        except openai.error.InvalidRequestError as e:
            logging.exception(e)
            return f"⚠️ _OpenAI Invalid request_ ⚠️\n{str(e)}"

        except Exception as e:
            logging.exception(e)
            return f"⚠️ _An error has occurred_ ⚠️\n{str(e)}"

    async def generate_image(self, prompt: str) -> tuple[str, str]:
        """
        Generates an image from the given prompt using DALL·E model.
        :param prompt: The prompt to send to the model
        :return: The image URL and the image size
        """
        response = await openai.Image.acreate(
            prompt=prompt,
            n=1,
            size=self.config['image_size']
        )
        return response['data'][0]['url'], self.config['image_size']

    async def transcribe(self, filename):
        """
        Transcribes the audio file using the Whisper model.
        """
        with open(filename, "rb") as audio:
            result = await openai.Audio.atranscribe("whisper-1", audio)
            return result.text

    def reset_chat_history(self, chat_id):
        """
        Resets the conversation history.
        """
        self.conversations[chat_id] = [{"role": "system", "content": self.config['assistant_prompt']}]

    def __max_age_reached(self, chat_id) -> bool:
        """
        Checks if the maximum conversation age has been reached.
        :param chat_id: The chat ID
        :return: A boolean indicating whether the maximum conversation age has been reached
        """
        if chat_id not in self.last_updated:
            return False
        last_updated = self.last_updated[chat_id]
        now = datetime.datetime.now()
        max_age_minutes = self.config['max_conversation_age_minutes']
        return last_updated < now - datetime.timedelta(minutes=max_age_minutes)

    def __add_to_history(self, chat_id, role, content):
        """
        Adds a message to the conversation history.
        :param chat_id: The chat ID
        :param role: The role of the message sender
        :param content: The message content
        """
        self.conversations[chat_id].append({"role": role, "content": content})

    async def __summarise(self, conversation) -> str:
        """
        Summarises the conversation history.
        :param conversation: The conversation history
        :return: The summary
        """
        messages = [
            { "role": "assistant", "content": "Summarize this conversation in 700 characters or less" },
            { "role": "user", "content": str(conversation) }
        ]
        response = await openai.ChatCompletion.acreate(
            model=self.config['model'],
            messages=messages,
            temperature=0.4
        )
        return response.choices[0]['message']['content']

    def __max_model_tokens(self):
        if self.config['model'] == "gpt-3.5-turbo" or self.config['model'] == "gpt-3.5-turbo-0301":
            return 4096
        raise NotImplementedError(
            f"Max tokens for model {self.config['model']} is not implemented yet."
        )

    # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    def __count_tokens(self, messages):
        """
        Counts the number of tokens required to send the given messages.
        :param messages: the messages to send
        :return: the number of tokens required
        """
        try:
            model = self.config['model']
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("gpt-3.5-turbo")
        if model == "gpt-3.5-turbo" or model == "gpt-3.5-turbo-0301":
            num_tokens = 0
            for message in messages:
                num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
                for key, value in message.items():
                    num_tokens += len(encoding.encode(value))
                    if key == "name":  # if there's a name, the role is omitted
                        num_tokens += -1  # role is always required and always 1 token
            num_tokens += 2  # every reply is primed with <im_start>assistant
            return num_tokens
        else:
            raise NotImplementedError(f"__count_tokens() is not presently implemented for model {model}")
