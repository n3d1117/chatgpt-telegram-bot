from __future__ import annotations
import datetime
import logging
import os

import tiktoken

import openai

import json
import httpx
import io
from PIL import Image

from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from utils import is_direct_result, encode_image, decode_image
from plugin_manager import PluginManager

# Models can be found here: https://platform.openai.com/docs/models/overview
# Models gpt-3.5-turbo-0613 and  gpt-3.5-turbo-16k-0613 will be deprecated on June 13, 2024
GPT_3_MODELS = ("gpt-3.5-turbo", "gpt-3.5-turbo-0301", "gpt-3.5-turbo-0613")
GPT_3_16K_MODELS = ("gpt-3.5-turbo-16k", "gpt-3.5-turbo-16k-0613", "gpt-3.5-turbo-1106", "gpt-3.5-turbo-0125")
GPT_4_MODELS = ("gpt-4", "gpt-4-0314", "gpt-4-0613", "gpt-4-turbo-preview")
GPT_4_32K_MODELS = ("gpt-4-32k", "gpt-4-32k-0314", "gpt-4-32k-0613")
GPT_4_VISION_MODELS = ("gpt-4o",)
GPT_4_128K_MODELS = ("gpt-4-1106-preview", "gpt-4-0125-preview", "gpt-4-turbo-preview", "gpt-4-turbo", "gpt-4-turbo-2024-04-09", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4.5", "gpt-4.5-turbo")
GPT_4O_MODELS = ("gpt-4o", "gpt-4o-mini", "chatgpt-4o-latest")
O_MODELS = ("o1", "o1-mini", "o1-preview", "o3", "o3-mini")
GPT_5_MODELS = ("gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5-2025-08-07", "gpt-5-chat-latest", "gpt-5-pro", "gpt-5.1", "gpt-5.1-chat-latest", "gpt-5.2", "gpt-5.2-pro", "gpt-5.2-chat-latest")
GPT_5_CODEX_MODELS = ("gpt-5-codex", "gpt-5.1-codex", "gpt-5.1-codex-mini", "gpt-5.1-codex-max")
GPT_ALL_MODELS = GPT_3_MODELS + GPT_3_16K_MODELS + GPT_4_MODELS + GPT_4_32K_MODELS + GPT_4_VISION_MODELS + GPT_4_128K_MODELS + GPT_4O_MODELS + O_MODELS + GPT_5_MODELS + GPT_5_CODEX_MODELS

def default_max_tokens(model: str) -> int:
    """
    Gets the default number of max tokens for the given model.
    :param model: The model name
    :return: The default number of max tokens
    """
    base = 1200
    if model in GPT_3_MODELS:
        return base
    elif model in GPT_4_MODELS:
        return base * 2
    elif model in GPT_3_16K_MODELS:
        if model == "gpt-3.5-turbo-1106":
            return 4096
        return base * 4
    elif model in GPT_4_32K_MODELS:
        return base * 8
    elif model in GPT_4_VISION_MODELS:
        return 4096
    elif model in GPT_4_128K_MODELS:
        return 4096
    elif model in GPT_4O_MODELS:
        return 4096
    elif model in O_MODELS:
        return 4096
    elif model in GPT_5_MODELS or model in GPT_5_CODEX_MODELS:
        return 8192
    return 1200  # Default fallback for unknown models


def are_functions_available(model: str) -> bool:
    """
    Whether the given model supports functions
    """
    if model in ("gpt-3.5-turbo-0301", "gpt-4-0314", "gpt-4-32k-0314", "gpt-3.5-turbo-0613", "gpt-3.5-turbo-16k-0613"):
        return False
    if model in O_MODELS:
        return False
    return True


# Load translations
parent_dir_path = os.path.join(os.path.dirname(__file__), os.pardir)
translations_file_path = os.path.join(parent_dir_path, 'translations.json')
with open(translations_file_path, 'r', encoding='utf-8') as f:
    translations = json.load(f)


def localized_text(key, bot_language):
    """
    Return translated text for a key in specified bot_language.
    Keys and translations can be found in the translations.json.
    """
    try:
        return translations[bot_language][key]
    except KeyError:
        logging.warning(f"No translation available for bot_language code '{bot_language}' and key '{key}'")
        # Fallback to English if the translation is not available
        if key in translations['en']:
            return translations['en'][key]
        else:
            logging.warning(f"No english definition found for key '{key}' in translations.json")
            # return key as text
            return key



class Delta:
    def __init__(self, role=None, content=None, type=None, function_call=None):
        self.role = role
        self.content = content
        self.function_call = function_call
        self.type = type

class StreamChoice:
    def __init__(self, delta, finish_reason=None):
        self.delta = delta
        self.finish_reason = finish_reason

class StreamChunk:
    def __init__(self, choices):
        self.choices = choices

class OpenAIHelper:
    """
    ChatGPT helper class.
    """

    def __init__(self, config: dict, plugin_manager: PluginManager):
        """
        Initializes the OpenAI helper class with the given configuration.
        :param config: A dictionary containing the GPT configuration
        :param plugin_manager: The plugin manager
        """
        http_client = httpx.AsyncClient(proxy=config['proxy']) if 'proxy' in config else None
        self.client = openai.AsyncOpenAI(api_key=config['api_key'], http_client=http_client)
        self.config = config
        self.plugin_manager = plugin_manager
        self.conversations: dict[int: list] = {}  # {chat_id: history}
        self.conversations_vision: dict[int: bool] = {}  # {chat_id: is_vision}
        self.last_updated: dict[int: datetime] = {}  # {chat_id: last_update_timestamp}

    def get_conversation_stats(self, chat_id: int) -> tuple[int, int]:
        """
        Gets the number of messages and tokens used in the conversation.
        :param chat_id: The chat ID
        :return: A tuple containing the number of messages and tokens used
        """
        if chat_id not in self.conversations:
            self.reset_chat_history(chat_id)
        return len(self.conversations[chat_id]), self.__count_tokens(self.conversations[chat_id])

    async def get_chat_response(self, chat_id: int, query: str) -> tuple[str, str]:
        """
        Gets a full response from the GPT model.
        :param chat_id: The chat ID
        :param query: The query to send to the model
        :return: The answer from the model and the number of tokens used
        """
        plugins_used = ()
        response = await self.__common_get_chat_response(chat_id, query)
        if self.config['enable_functions'] and not self.conversations_vision[chat_id]:
            response, plugins_used = await self.__handle_function_call(chat_id, response)
            if is_direct_result(response):
                return response, '0'

        answer = ''

        if len(response.choices) > 1 and self.config['n_choices'] > 1:
            for index, choice in enumerate(response.choices):
                content = choice.message.content.strip()
                if index == 0:
                    self.__add_to_history(chat_id, role="assistant", content=content)
                answer += f'{index + 1}\u20e3\n'
                answer += content
                answer += '\n\n'
        else:
            answer = response.choices[0].message.content.strip()
            self.__add_to_history(chat_id, role="assistant", content=answer)

        bot_language = self.config['bot_language']
        show_plugins_used = len(plugins_used) > 0 and self.config['show_plugins_used']
        plugin_names = tuple(self.plugin_manager.get_plugin_source_name(plugin) for plugin in plugins_used)
        if self.config['show_usage']:
            answer += "\n\n---\n" \
                      f"💰 {str(response.usage.total_tokens)} {localized_text('stats_tokens', bot_language)}" \
                      f" ({str(response.usage.prompt_tokens)} {localized_text('prompt', bot_language)}," \
                      f" {str(response.usage.completion_tokens)} {localized_text('completion', bot_language)})"
            if show_plugins_used:
                answer += f"\n🔌 {', '.join(plugin_names)}"
        elif show_plugins_used:
            answer += f"\n\n---\n🔌 {', '.join(plugin_names)}"

        return answer, response.usage.total_tokens

    async def get_chat_response_stream(self, chat_id: int, query: str):
        """
        Stream response from the GPT model.
        :param chat_id: The chat ID
        :param query: The query to send to the model
        :return: The answer from the model and the number of tokens used, or 'not_finished'
        """
        plugins_used = ()
        response = await self.__common_get_chat_response(chat_id, query, stream=True)
        if self.config['enable_functions'] and not self.conversations_vision[chat_id]:
            response, plugins_used = await self.__handle_function_call(chat_id, response, stream=True)
            if is_direct_result(response):
                yield response, '0'
                return

        answer = ''
        async for chunk in response:
            if len(chunk.choices) == 0:
                continue
            delta = chunk.choices[0].delta
            # Check for reasoning status
            if getattr(delta, 'type', None) == 'reasoning':
                yield "🤔 Thinking...", 'not_finished'
                continue
            
            if getattr(delta, 'type', None) == 'tool_status':
                yield delta.content, 'not_finished'
                continue

            if delta.content:
                answer += delta.content
                yield answer, 'not_finished'
        answer = answer.strip()
        self.__add_to_history(chat_id, role="assistant", content=answer)
        tokens_used = str(self.__count_tokens(self.conversations[chat_id]))

        show_plugins_used = len(plugins_used) > 0 and self.config['show_plugins_used']
        plugin_names = tuple(self.plugin_manager.get_plugin_source_name(plugin) for plugin in plugins_used)
        if self.config['show_usage']:
            answer += f"\n\n---\n💰 {tokens_used} {localized_text('stats_tokens', self.config['bot_language'])}"
            if show_plugins_used:
                answer += f"\n🔌 {', '.join(plugin_names)}"
        elif show_plugins_used:
            answer += f"\n\n---\n🔌 {', '.join(plugin_names)}"

        yield answer, tokens_used

    @retry(
        reraise=True,
        retry=retry_if_exception_type(openai.RateLimitError),
        wait=wait_fixed(20),
        stop=stop_after_attempt(3)
    )
    async def __common_get_chat_response(self, chat_id: int, query: str, stream=False):
        """
        Request a response from the GPT model.
        :param chat_id: The chat ID
        :param query: The query to send to the model
        :return: The answer from the model and the number of tokens used
        """
        bot_language = self.config['bot_language']
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
                    self.reset_chat_history(chat_id, self.conversations[chat_id][0]['content'])
                    self.__add_to_history(chat_id, role="assistant", content=summary)
                    self.__add_to_history(chat_id, role="user", content=query)
                except Exception as e:
                    logging.warning(f'Error while summarising chat history: {str(e)}. Popping elements instead...')
                    self.conversations[chat_id] = self.conversations[chat_id][-self.config['max_history_size']:]

            max_tokens_str = 'max_completion_tokens' if self.config['model'] in O_MODELS or self.config['model'] in GPT_5_MODELS or self.config['model'] in GPT_5_CODEX_MODELS else 'max_tokens'
            common_args = {
                'model': self.config['model'] if not self.conversations_vision[chat_id] else self.config['vision_model'],
                'messages': self.conversations[chat_id],
                'temperature': self.config['temperature'],
                'n': self.config['n_choices'],
                max_tokens_str: self.config['max_tokens'],
                'presence_penalty': self.config['presence_penalty'],
                'frequency_penalty': self.config['frequency_penalty'],
                'stream': stream
            }

            if self.config['model'] in GPT_5_MODELS or self.config['model'] in GPT_5_CODEX_MODELS:
                return await self._generate_gpt5_response(chat_id, stream=stream)

            # Legacy Chat Completion API for other models
            if self.config['enable_functions'] and not self.conversations_vision[chat_id]:
                functions = self.plugin_manager.get_functions_specs()
                if len(functions) > 0:
                    common_args['functions'] = functions
                    common_args['function_call'] = 'auto'
            return await self.client.chat.completions.create(**common_args)

        except openai.RateLimitError as e:
            raise e

        except openai.BadRequestError as e:
            raise Exception(f"⚠️ _{localized_text('openai_invalid', bot_language)}._ ⚠️\n{str(e)}") from e

        except Exception as e:
            raise Exception(f"⚠️ _{localized_text('error', bot_language)}._ ⚠️\n{str(e)}") from e

    async def __handle_function_call(self, chat_id, response, stream=False, times=0, plugins_used=()):
        if stream:
            async def stream_middleware():
                function_name = ''
                arguments = ''
                is_collecting_function = False
                
                async for chunk in response:
                    if len(chunk.choices) == 0:
                        continue
                    
                    delta = chunk.choices[0].delta
                    
                    # Pass through reasoning and tool_status
                    if getattr(delta, 'type', None) in ['reasoning', 'tool_status']:
                        yield chunk
                        continue

                    # Check for function call
                    if delta.function_call:
                        is_collecting_function = True
                        if delta.function_call.name:
                            function_name += delta.function_call.name
                        if delta.function_call.arguments:
                            arguments += delta.function_call.arguments
                        continue # Don't yield function call bits to the consumer

                    # Pass through content
                    if delta.content:
                        yield chunk
                
                # Stream finished, check if we captured a function call
                if is_collecting_function:
                    logging.info(f'Calling function {function_name} with arguments {arguments}')
                    
                    # Yield status
                    yield StreamChunk([StreamChoice(Delta(type='tool_status', content=f"🔎 Using {function_name}..."))])
                    
                    # Execute
                    function_response = await self.plugin_manager.call_function(function_name, self, arguments)

                    # Handle execution result
                    if is_direct_result(function_response):
                        self.__add_function_call_to_history(chat_id=chat_id, function_name=function_name,
                                                            content=json.dumps({'result': 'Done, the content has been sent'
                                                                                          'to the user.'}))
                        return

                    self.__add_function_call_to_history(chat_id=chat_id, function_name=function_name, content=function_response)
                    
                    # Recursive call
                    new_plugins_used = plugins_used + (function_name,)
                    if self.config['model'] in GPT_5_MODELS or self.config['model'] in GPT_5_CODEX_MODELS:
                        next_response_stream = await self._generate_gpt5_response(
                            chat_id, 
                            stream=True, 
                            allow_functions=(times < self.config['functions_max_consecutive_calls'])
                        )
                    else:
                        next_response_stream = await self.client.chat.completions.create(
                            model=self.config['model'],
                            messages=self.conversations[chat_id],
                            functions=self.plugin_manager.get_functions_specs(),
                            function_call='auto' if times < self.config['functions_max_consecutive_calls'] else 'none',
                            stream=True
                        )
                    
                    # Wrap the next stream recursively
                    next_wrapper, _ = await self.__handle_function_call(chat_id, next_response_stream, stream=True, times=times+1, plugins_used=new_plugins_used)
                    async for item in next_wrapper:
                        yield item

            return stream_middleware(), plugins_used

        # Non-streaming logic (Legacy/Blocking)
        function_name = ''
        arguments = ''
        if len(response.choices) > 0:
            first_choice = response.choices[0]
            if first_choice.message.function_call:
                if first_choice.message.function_call.name:
                    function_name += first_choice.message.function_call.name
                if first_choice.message.function_call.arguments:
                    arguments += first_choice.message.function_call.arguments
            else:
                return response, plugins_used
        else:
            return response, plugins_used

        logging.info(f'Calling function {function_name} with arguments {arguments}')

        if stream:
            async def chained():
                # Yield status immediately
                yield StreamChunk([StreamChoice(Delta(type='tool_status', content=f"🔎 Using {function_name}..."))])
                
                # Execute function
                function_response = await self.plugin_manager.call_function(function_name, self, arguments)

                # Add to history
                if is_direct_result(function_response):
                    self.__add_function_call_to_history(chat_id=chat_id, function_name=function_name,
                                                        content=json.dumps({'result': 'Done, the content has been sent'
                                                                                      'to the user.'}))
                    return 

                self.__add_function_call_to_history(chat_id=chat_id, function_name=function_name, content=function_response)
                
                # Call next model turn
                if self.config['model'] in GPT_5_MODELS or self.config['model'] in GPT_5_CODEX_MODELS:
                    response = await self._generate_gpt5_response(
                         chat_id, 
                         stream=True, 
                         allow_functions=(times < self.config['functions_max_consecutive_calls'])
                    )
                else:
                    response = await self.client.chat.completions.create(
                        model=self.config['model'],
                        messages=self.conversations[chat_id],
                        functions=self.plugin_manager.get_functions_specs(),
                        function_call='auto' if times < self.config['functions_max_consecutive_calls'] else 'none',
                        stream=True
                    )
                
                # Recursive call
                next_response_tuple = await self.__handle_function_call(chat_id, response, stream=True, times=times + 1, plugins_used=plugins_used + (function_name,))
                async for item in next_response_tuple[0]:
                    yield item

            return chained(), plugins_used + (function_name,)

        # Non-streaming logic
        function_response = await self.plugin_manager.call_function(function_name, self, arguments)

        if function_name not in plugins_used:
            plugins_used += (function_name,)

        if is_direct_result(function_response):
            self.__add_function_call_to_history(chat_id=chat_id, function_name=function_name,
                                                content=json.dumps({'result': 'Done, the content has been sent'
                                                                              'to the user.'}))
            return function_response, plugins_used

        self.__add_function_call_to_history(chat_id=chat_id, function_name=function_name, content=function_response)
        if self.config['model'] in GPT_5_MODELS or self.config['model'] in GPT_5_CODEX_MODELS:
            response = await self._generate_gpt5_response(
                 chat_id, 
                 stream=stream, 
                 allow_functions=(times < self.config['functions_max_consecutive_calls'])
            )
        else:
            response = await self.client.chat.completions.create(
                model=self.config['model'],
                messages=self.conversations[chat_id],
                functions=self.plugin_manager.get_functions_specs(),
                function_call='auto' if times < self.config['functions_max_consecutive_calls'] else 'none',
                stream=stream
            )
        return await self.__handle_function_call(chat_id, response, stream, times + 1, plugins_used)

    async def generate_image(self, prompt: str) -> tuple[str, str]:
        """
        Generates an image from the given prompt using DALL·E model.
        :param prompt: The prompt to send to the model
        :return: The image URL and the image size
        """
        bot_language = self.config['bot_language']
        try:
            response = await self.client.images.generate(
                prompt=prompt,
                n=1,
                model=self.config['image_model'],
                size=self.config['image_size']
            )

            if len(response.data) == 0:
                logging.error(f'No response from GPT: {str(response)}')
                raise Exception(
                    f"⚠️ _{localized_text('error', bot_language)}._ "
                    f"⚠️\n{localized_text('try_again', bot_language)}."
                )

            return response.data[0].url, self.config['image_size']
        except Exception as e:
            raise Exception(f"⚠️ _{localized_text('error', bot_language)}._ ⚠️\n{str(e)}") from e


    async def generate_speech(self, text: str) -> tuple[any, int]:
        """
        Generates an audio from the given text using TTS model.
        :param prompt: The text to send to the model
        :return: The audio in bytes and the text size
        """
        bot_language = self.config['bot_language']
        try:
            response = await self.client.audio.speech.create(
                model=self.config['tts_model'],
                voice=self.config['tts_voice'],
                input=text,
                response_format='opus'
            )

            temp_file = io.BytesIO()
            temp_file.write(response.read())
            temp_file.seek(0)
            return temp_file, len(text)
        except Exception as e:
            raise Exception(f"⚠️ _{localized_text('error', bot_language)}._ ⚠️\n{str(e)}") from e

    async def transcribe(self, filename):
        """
        Transcribes the audio file using the Whisper model.
        """
        try:
            with open(filename, "rb") as audio:
                prompt_text = self.config['whisper_prompt']
                result = await self.client.audio.transcriptions.create(model="whisper-1", file=audio, prompt=prompt_text)
                return result.text
        except Exception as e:
            logging.exception(e)
            raise Exception(f"⚠️ _{localized_text('error', self.config['bot_language'])}._ ⚠️\n{str(e)}") from e

    @retry(
        reraise=True,
        retry=retry_if_exception_type(openai.RateLimitError),
        wait=wait_fixed(20),
        stop=stop_after_attempt(3)
    )
    async def __common_get_chat_response_vision(self, chat_id: int, content: list, stream=False):
        """
        Request a response from the GPT model.
        :param chat_id: The chat ID
        :param query: The query to send to the model
        :return: The answer from the model and the number of tokens used
        """
        bot_language = self.config['bot_language']
        try:
            if chat_id not in self.conversations or self.__max_age_reached(chat_id):
                self.reset_chat_history(chat_id)

            self.last_updated[chat_id] = datetime.datetime.now()

            if self.config['enable_vision_follow_up_questions']:
                self.conversations_vision[chat_id] = True
                self.__add_to_history(chat_id, role="user", content=content)
            else:
                for message in content:
                    if message['type'] == 'text':
                        query = message['text']
                        break
                self.__add_to_history(chat_id, role="user", content=query)

            # Summarize the chat history if it's too long to avoid excessive token usage
            token_count = self.__count_tokens(self.conversations[chat_id])
            exceeded_max_tokens = token_count + self.config['max_tokens'] > self.__max_model_tokens()
            exceeded_max_history_size = len(self.conversations[chat_id]) > self.config['max_history_size']

            if exceeded_max_tokens or exceeded_max_history_size:
                logging.info(f'Chat history for chat ID {chat_id} is too long. Summarising...')
                try:
                    
                    last = self.conversations[chat_id][-1]
                    summary = await self.__summarise(self.conversations[chat_id][:-1])
                    logging.debug(f'Summary: {summary}')
                    self.reset_chat_history(chat_id, self.conversations[chat_id][0]['content'])
                    self.__add_to_history(chat_id, role="assistant", content=summary)
                    self.conversations[chat_id] += [last]
                except Exception as e:
                    logging.warning(f'Error while summarising chat history: {str(e)}. Popping elements instead...')
                    self.conversations[chat_id] = self.conversations[chat_id][-self.config['max_history_size']:]

            message = {'role':'user', 'content':content}

            common_args = {
                'model': self.config['vision_model'],
                'messages': self.conversations[chat_id][:-1] + [message],
                'temperature': self.config['temperature'],
                'n': 1, # several choices is not implemented yet
                'max_tokens': self.config['vision_max_tokens'],
                'presence_penalty': self.config['presence_penalty'],
                'frequency_penalty': self.config['frequency_penalty'],
                'stream': stream
            }


            # vision model does not yet support functions

            # if self.config['enable_functions']:
            #     functions = self.plugin_manager.get_functions_specs()
            #     if len(functions) > 0:
            #         common_args['functions'] = self.plugin_manager.get_functions_specs()
            #         common_args['function_call'] = 'auto'
            
            return await self.client.chat.completions.create(**common_args)

        except openai.RateLimitError as e:
            raise e

        except openai.BadRequestError as e:
            raise Exception(f"⚠️ _{localized_text('openai_invalid', bot_language)}._ ⚠️\n{str(e)}") from e

        except Exception as e:
            raise Exception(f"⚠️ _{localized_text('error', bot_language)}._ ⚠️\n{str(e)}") from e


    async def interpret_image(self, chat_id, fileobj, prompt=None):
        """
        Interprets a given PNG image file using the Vision model.
        """
        image = encode_image(fileobj)
        prompt = self.config['vision_prompt'] if prompt is None else prompt

        content = [{'type':'text', 'text':prompt}, {'type':'image_url', \
                    'image_url': {'url':image, 'detail':self.config['vision_detail'] } }]

        response = await self.__common_get_chat_response_vision(chat_id, content)

        

        # functions are not available for this model
        
        # if self.config['enable_functions']:
        #     response, plugins_used = await self.__handle_function_call(chat_id, response)
        #     if is_direct_result(response):
        #         return response, '0'

        answer = ''

        if len(response.choices) > 1 and self.config['n_choices'] > 1:
            for index, choice in enumerate(response.choices):
                content = choice.message.content.strip()
                if index == 0:
                    self.__add_to_history(chat_id, role="assistant", content=content)
                answer += f'{index + 1}\u20e3\n'
                answer += content
                answer += '\n\n'
        else:
            answer = response.choices[0].message.content.strip()
            self.__add_to_history(chat_id, role="assistant", content=answer)

        bot_language = self.config['bot_language']
        # Plugins are not enabled either
        # show_plugins_used = len(plugins_used) > 0 and self.config['show_plugins_used']
        # plugin_names = tuple(self.plugin_manager.get_plugin_source_name(plugin) for plugin in plugins_used)
        if self.config['show_usage']:
            answer += "\n\n---\n" \
                      f"💰 {str(response.usage.total_tokens)} {localized_text('stats_tokens', bot_language)}" \
                      f" ({str(response.usage.prompt_tokens)} {localized_text('prompt', bot_language)}," \
                      f" {str(response.usage.completion_tokens)} {localized_text('completion', bot_language)})"
            # if show_plugins_used:
            #     answer += f"\n🔌 {', '.join(plugin_names)}"
        # elif show_plugins_used:
        #     answer += f"\n\n---\n🔌 {', '.join(plugin_names)}"

        return answer, response.usage.total_tokens

    async def interpret_image_stream(self, chat_id, fileobj, prompt=None):
        """
        Interprets a given PNG image file using the Vision model.
        """
        image = encode_image(fileobj)
        prompt = self.config['vision_prompt'] if prompt is None else prompt

        content = [{'type':'text', 'text':prompt}, {'type':'image_url', \
                    'image_url': {'url':image, 'detail':self.config['vision_detail'] } }]

        response = await self.__common_get_chat_response_vision(chat_id, content, stream=True)

        

        # if self.config['enable_functions']:
        #     response, plugins_used = await self.__handle_function_call(chat_id, response, stream=True)
        #     if is_direct_result(response):
        #         yield response, '0'
        #         return

        answer = ''
        async for chunk in response:
            if len(chunk.choices) == 0:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                answer += delta.content
                yield answer, 'not_finished'
        answer = answer.strip()
        self.__add_to_history(chat_id, role="assistant", content=answer)
        tokens_used = str(self.__count_tokens(self.conversations[chat_id]))

        #show_plugins_used = len(plugins_used) > 0 and self.config['show_plugins_used']
        #plugin_names = tuple(self.plugin_manager.get_plugin_source_name(plugin) for plugin in plugins_used)
        if self.config['show_usage']:
            answer += f"\n\n---\n💰 {tokens_used} {localized_text('stats_tokens', self.config['bot_language'])}"
        #     if show_plugins_used:
        #         answer += f"\n🔌 {', '.join(plugin_names)}"
        # elif show_plugins_used:
        #     answer += f"\n\n---\n🔌 {', '.join(plugin_names)}"

        yield answer, tokens_used

    def reset_chat_history(self, chat_id, content=''):
        """
        Resets the conversation history.
        """
        if content == '':
            content = self.config['assistant_prompt']
        # Determine the appropriate role for system prompt
        if self.config['model'] in O_MODELS:
            role = "assistant"
        elif self.config['model'] in GPT_5_MODELS or self.config['model'] in GPT_5_CODEX_MODELS:
            role = "developer"
        else:
            role = "system"
        self.conversations[chat_id] = [{"role": role, "content": content}]
        self.conversations_vision[chat_id] = False

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

    async def _generate_gpt5_response(self, chat_id, stream=False, allow_functions=True):
        """
        Refactored implementation using the client.responses.create API for GPT-5 models.
        Adapts Responses API events to the ChatCompletionChunk format expected by consumers.
        """
        # Prepare Input Items from Conversation History
        input_items = []
        for msg in self.conversations[chat_id]:
            role = msg['role']
            content = msg['content']
            
            if role == 'function':
                # Map legacy 'function' role to 'function_call_output' item
                # Generate a consistent (fake) call_id since legacy history lacks it
                call_id = f"call_{msg.get('name', 'unknown')}"
                input_items.append({
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": str(content)
                })
            elif role in ['user', 'system', 'developer', 'assistant']:
                # Map 'system' to 'developer' for GPT-5 Responses API
                if role == 'system':
                    role = 'developer'
                # Pass as standard message item
                input_items.append({
                    "type": "message",
                    "role": role,
                    "content": content
                })
            # Ignore unknown roles

        # Prepare Tools and Include Parameters
        tools_arg = []
        include_arg = []
        
        # Native Features
        if self.config.get('enable_web_search'):
            tools_arg.append({"type": "web_search"})
            include_arg.append("web_search_call.action.sources")
            
        if self.config.get('enable_file_search'):
            v_id = self.config.get('file_search_vector_store_ids')
            if v_id:
                tools_arg.append({"type": "file_search", "file_search": {"vector_store_ids": v_id.split(',')}})
                include_arg.append("file_search_call.results")

        if self.config.get('enable_code_interpreter'):
             tools_arg.append({"type": "code_interpreter"})
             include_arg.append("code_interpreter_call.outputs")

        if self.config.get('enable_mcp') and self.config.get('mcp_server_url'):
            tools_arg.append({
                "type": "mcp",
                "server_label": self.config.get('mcp_server_label', 'default_mcp'),
                "server_url": self.config.get('mcp_server_url'),
                "require_approval": "never"
            })

        # Custom Functions
        if self.config.get('enable_functions') and allow_functions:
            functions = self.plugin_manager.get_functions_specs()
            for func in functions:
                tools_arg.append({"type": "function", "function": func})

        # Request Parameters
        params = {
            "model": self.config['model'],
            "input": input_items,
            "stream": True, # Always stream to handle events
        }
        
        if tools_arg:
            params['tools'] = tools_arg
            # Add tool_choice to control when tools are used
            tool_choice = self.config.get('tool_choice', 'auto')
            if tool_choice in ['auto', 'required', 'none']:
                params['tool_choice'] = tool_choice
        if include_arg:
            params['include'] = include_arg
        if self.config['reasoning_effort'] != 'none':
             params['reasoning'] = {'effort': self.config['reasoning_effort']}
        if self.config.get('verbosity'):
             params['text'] = {'verbosity': self.config['verbosity']}

        # Perform API Call
        try:
            response_stream = await self.client.responses.create(**params)
        except Exception as e:
            logging.error(f"GPT-5 API Error: {e}")
            bot_language = self.config['bot_language']
            raise Exception(f"⚠️ _{localized_text('error', bot_language)}._ ⚠️\n{str(e)}") from e

        # Stream Adapter
        async def response_adapter():
            # Initial chunk to satisfy consumers waiting for a role
            yield StreamChunk([StreamChoice(Delta(role='assistant', content=''))])
            
            reasoning_started = False
            async for event in response_stream:
                if event.type == 'response.output_text.delta':
                    yield StreamChunk([StreamChoice(Delta(content=event.delta))])
                
                elif event.type == 'response.reasoning_text.delta':
                     yield StreamChunk([StreamChoice(Delta(type='reasoning'))])

                elif event.type == 'response.in_progress' and not reasoning_started:
                     reasoning_started = True
                     yield StreamChunk([StreamChoice(Delta(type='reasoning'))])

                elif event.type == 'response.output_item.added':
                     pass

                elif event.type == 'response.function_call_arguments.delta':
                     # Function call details streaming
                     fc_stub = type('FunctionCallStub', (object,), {'name': None, 'arguments': event.delta})
                     yield StreamChunk([StreamChoice(Delta(function_call=fc_stub))])
                
                elif event.type == 'response.function_call.delta':
                     # Newer event type for some tools
                     fc_stub = type('FunctionCallStub', (object,), {
                         'name': getattr(event, 'function_name', None), 
                         'arguments': getattr(event, 'function_arguments', None)
                     })
                     yield StreamChunk([StreamChoice(Delta(function_call=fc_stub))])

                elif event.type == 'response.output_text.done':
                    pass

                # Handle Tool Status Events (Visual Feedback)
                elif 'searching' in event.type or 'in_progress' in event.type:
                     status_msg = ""
                     if 'web_search' in event.type: status_msg = "🔎 Searching the web..."
                     elif 'file_search' in event.type: status_msg = "📂 Searching files..."
                     elif 'code_interpreter' in event.type: status_msg = "🐍 Running code..."
                     elif 'computer' in event.type: status_msg = "💻 Using computer..."
                     elif 'function_call' in event.type: pass 
                     
                     if status_msg:
                         yield StreamChunk([StreamChoice(Delta(type='tool_status', content=status_msg))])

        if stream:
            return response_adapter()
        else:
            # Aggregate if non-stream requested (legacy support)
            full_content = ""
            async for chunk in response_adapter():
                d = chunk.choices[0].delta
                if d.content:
                    full_content += d.content
            
            # Construct mock object with usage tracking
            class MockResponse:
                def __init__(self, content):
                    self.choices = [type('Choice', (object,), {'message': type('Message', (object,), {'content': content, 'function_call': None, 'tool_calls': None})()})]
                    # Estimate token usage since Responses API doesn't provide it in same format
                    self.usage = type('Usage', (object,), {
                        'total_tokens': 0,
                        'prompt_tokens': 0,
                        'completion_tokens': 0
                    })()
            return MockResponse(full_content)

    def __add_function_call_to_history(self, chat_id, function_name, content):
        """
        Adds a function call to the conversation history
        """
        self.conversations[chat_id].append({"role": "function", "name": function_name, "content": content})

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
        if self.config['model'] in GPT_5_MODELS or self.config['model'] in GPT_5_CODEX_MODELS:
            # Use Responses API for GPT-5 models
            input_items = [
                {"type": "message", "role": "developer", "content": "Summarize this conversation in 700 characters or less"},
                {"type": "message", "role": "user", "content": str(conversation)}
            ]
            response = await self.client.responses.create(
                model=self.config['model'],
                input=input_items
            )
            # Extract text from response output
            if hasattr(response, 'output_text'):
                return response.output_text
            # Fallback: iterate through output items
            for item in response.output:
                if hasattr(item, 'content'):
                    for content_block in item.content:
                        if hasattr(content_block, 'text'):
                            return content_block.text
            return str(response.output)
        else:
            messages = [
                {"role": "assistant", "content": "Summarize this conversation in 700 characters or less"},
                {"role": "user", "content": str(conversation)}
            ]
            response = await self.client.chat.completions.create(
                model=self.config['model'],
                messages=messages,
                temperature=1 if self.config['model'] in O_MODELS else 0.4
            )
            return response.choices[0].message.content
    
    def __max_model_tokens(self):
        base = 4096
        model = self.config['model']
        if model in GPT_3_MODELS:
            return base
        if model in GPT_3_16K_MODELS:
            return base * 4
        if model in GPT_4_MODELS:
            return base * 2
        if model in GPT_4_32K_MODELS:
            return base * 8
        if model in GPT_4_VISION_MODELS:
            return base * 31
        if model in GPT_4_128K_MODELS:
            return base * 31
        if model in GPT_4O_MODELS:
            return base * 31
        if model in O_MODELS:
            if model == "o1":
                return 100_000
            elif model == "o1-preview":
                return 32_768
            else:
                return 65_536
        if model in GPT_5_MODELS or model in GPT_5_CODEX_MODELS:
            if "gpt-5.2" in model or "gpt-5.1-codex-max" in model:
                return 400_000
            return 200_000  # GPT-5 models support 200k context window
        raise NotImplementedError(f"Max tokens for model {model} is not implemented yet.")

    def __count_tokens(self, messages) -> int:
        model = self.config['model']
        try:
            encoding = tiktoken.encoding_for_model(model)
        except (KeyError, ValueError):
            try:
                encoding = tiktoken.get_encoding("o200k_base")
            except ValueError:
                encoding = tiktoken.get_encoding("cl100k_base")

        tokens_per_message = 3
        tokens_per_name = 1
        num_tokens = 0

        for message in messages:
            num_tokens += tokens_per_message
            for key, value in message.items():
                if key == 'content':
                    if isinstance(value, str):
                        num_tokens += len(encoding.encode(value))
                    else:
                        for message1 in value:
                            if message1['type'] == 'image_url':
                                image = decode_image(message1['image_url']['url'])
                                num_tokens += self.__count_tokens_vision(image)
                            else:
                                num_tokens += len(encoding.encode(message1['text']))
                else:
                    num_tokens += len(encoding.encode(value))
                    if key == "name":
                        num_tokens += tokens_per_name
        num_tokens += 3
        return num_tokens

    def __count_tokens_vision(self, image_bytes: bytes) -> int:
        import io
        from PIL import Image

        image_file = io.BytesIO(image_bytes)
        image = Image.open(image_file)
        model = self.config['vision_model']
        if model not in GPT_4_VISION_MODELS:
            if model in GPT_5_MODELS or model in GPT_5_CODEX_MODELS or model in GPT_4O_MODELS:
                # Use same estimation formula for GPT-5 and GPT-4o models
                pass  # Continue with the calculation below
            else:
                raise NotImplementedError(f"""count_tokens_vision() is not implemented for model {model}.""")

        w, h = image.size
        if w > h: w, h = h, w
        base_tokens = 85
        detail = self.config['vision_detail']
        if detail == 'low':
            return base_tokens
        elif detail in ['high', 'auto']:
            f = max(w / 768, h / 2048)
            if f > 1:
                w, h = int(w / f), int(h / f)
            tw, th = (w + 511) // 512, (h + 511) // 512
            tiles = tw * th
            return base_tokens + tiles * 170
        else:
            raise NotImplementedError(f"unknown parameter detail={detail} for model {model}.")


