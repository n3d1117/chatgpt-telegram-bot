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

    def reset_history(self):
        """
        Resets the conversation history.
        """
        self.history = self.initial_history

if __name__ == '__main__':
    gpt = GPTHelper({'api_key': 'YOUR_API_KEY'})

    while True:
        query = input("You: ")
        print("AI: {}".format(gpt.get_response(query)))