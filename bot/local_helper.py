import requests
import aiohttp

class LocalModelHelper:
    def __init__(self, base_url="http://localhost:1234/v1"):
        self.base_url = base_url

    def get_models(self):
        response = requests.get(f"{self.base_url}/v1/models")
        response.raise_for_status()
        return response.json()

    async def chat_completion(self, model, messages, temperature=1.0, max_tokens=512):
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                raise Exception(f"Local model error: {response.status}, {await response.text()}")

    async def chat_completion_stream(self, model, messages, temperature=1.0, max_tokens=512):
        """
        Stream chat completion responses from the local model.
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                async for line in response.content:
                    decoded_line = line.decode("utf-8").strip()
                    if decoded_line:  # Skip empty lines
                        yield decoded_line
