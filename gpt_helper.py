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
        self.prompt = "You are a helpful assistant. You answer with concise, straight-forward answers. You sometimes " \
                      "make jokes, if appropriate. You are never rude. You are always helpful."
        self.history = [{"role": "system", "content": self.prompt}]

    def get_response(self, query) -> str:
        """
        Gets a response from the GPT-3 model.
        :param query: The query to send to the model
        :return: The answer from the model
        """
        try:
            self.history.append({"role": "user", "content": query})

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=self.history
            )

            answer = response.choices[0]['message']['content']
            self.history.append({"role": "assistant", "content": answer})
            return answer
        except openai.error.RateLimitError as e:
            logging.exception(e)
            return "OpenAI RateLimit exceed"
        except Exception as e:
            logging.exception(e)
            return "Error"

    def reset(self):
        """
        Resets the conversation history.
        """
        self.history = [{"role": "system", "content": self.prompt}]
