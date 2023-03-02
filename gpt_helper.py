import logging
import openai


class GPTHelper:
    """
    ChatGPT helper class.
    """

    def __init__(self, config: dict):
        """
        Initializes the GPT helper class with the given configuration.
        :param config: A dictionary containing the GPT configuration
        """
        openai.api_key = config['api_key']
        self.config = config
        self.initial_history = [{"role": "system", "content": config['assistant_prompt']}]
        self.history = self.initial_history

    def get_response(self, query) -> str:
        """
        Gets a response from the GPT-3 model.
        :param query: The query to send to the model
        :return: The answer from the model
        """
        try:
            self.history.append({"role": "user", "content": query})

            response = openai.ChatCompletion.create(
                model=self.config['model'],
                messages=self.history,
                temperature=self.config['temperature'],
                n=self.config['n_choices'],
                max_tokens=self.config['max_tokens'],
                presence_penalty=self.config['presence_penalty'],
                frequency_penalty=self.config['frequency_penalty'],
            )

            if len(response.choices) > 0:
                if len(response.choices) > 1 and self.config['n_choices'] > 1:
                    answer = ''
                    for index, choice in enumerate(response.choices):
                        if index == 0:
                            self.history.append({"role": "assistant", "content": choice['message']['content']})
                        answer += f'{index+1}\u20e3\n'
                        answer += choice['message']['content']
                        answer += '\n\n'
                    return answer
                else:
                    answer = response.choices[0]['message']['content']
                    self.history.append({"role": "assistant", "content": answer})
                    return answer
            else:
                logging.error('No response from GPT-3')
                return "No response from GPT-3"

        except openai.error.RateLimitError as e:
            logging.exception(e)
            return "⚠️ _OpenAI RateLimit exceeded_ ⚠️\nPlease try again in a while."

        except Exception as e:
            logging.exception(e)
            return "Error"

    def reset_history(self):
        """
        Resets the conversation history.
        """
        self.history = self.initial_history
