import datetime
import json
import logging
import os
import uuid

import requests
from playwright.sync_api import sync_playwright


class ChatGPT3Bot:
    def __init__(self, config):
        self.config = config
        self.check_access_token()
        self.parent_id = self.generate_uuid()
        self.conversation_id = None

    def check_access_token(self):
        filename = 'access_token.json'

        def fetch_access_token():
            logging.info("Fetching access token...")
            response = self.extract_openai_access_token(self.config['openai_email'], self.config['openai_password'])
            if response:
                self.access_token = response['access_token']
                with open(filename, 'w') as f:
                    f.write(json.dumps(response))
            else:
                raise ValueError("Error: Unable to extract access token")

        if not os.path.exists(filename):
            fetch_access_token()
        else:
            with open(filename, 'r') as f:
                response = json.loads(f.read())
                if datetime.datetime.strptime(response["expires"], '%Y-%m-%d %H:%M:%S') < datetime.datetime.now():
                    logging.info("Access token expired, re-fetching...")
                    fetch_access_token()
                else:
                    self.access_token = response['access_token']

    def extract_openai_access_token(self, email, password) -> json:
        # This is a hacky way of extracting the access token
        # from the OpenAI chatbot. I'm using Playwright to
        # automate the login process and extract the token.
        with sync_playwright() as p:
            browser = p.webkit.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            # ---------------------
            page.goto("https://chat.openai.com/auth/login")
            page.get_by_role("button", name="Log in").click()
            page.get_by_label("Email address").fill(email)
            page.locator("button[name=\"action\"]").click()
            page.get_by_label("Password").click()
            page.get_by_label("Password").fill(password)
            page.get_by_role("button", name="Continue").click()
            # ---------------------
            with page.expect_response('**/auth/session', timeout=3000) as response:
                response_json = response.value.json()
                expiration_date = datetime.datetime.now() + datetime.timedelta(hours=1)
                context.close()
                browser.close()
                return {
                    'access_token': response_json['accessToken'],
                    'expires': expiration_date.strftime('%Y-%m-%d %H:%M:%S')
                }

    def generate_uuid(self) -> str:
        return str(uuid.uuid4())

    # Credits: https://github.com/acheong08/ChatGPT
    def get_chat_response(self, prompt) -> json:
        self.check_access_token()

        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer " + self.access_token,
            "Content-Type": "application/json"
        }
        data = {
            "action": "next",
            "messages": [{
                "id": str(self.generate_uuid()),
                "role": "user",
                "content": {"content_type": "text", "parts": [prompt]}
            }],
            "conversation_id": self.conversation_id,
            "parent_message_id": self.parent_id,
            "model": "text-davinci-002-render"
        }
        response = requests.post(
            "https://chat.openai.com/backend-api/conversation",
            headers=headers,
            data=json.dumps(data)
        )

        try:
            response = response.text.splitlines()[-4][6:]
            response = json.loads(response)
            self.parent_id = response["message"]["id"]
            self.conversation_id = response["conversation_id"]
            message = response["message"]["content"]["parts"][0]
            return {'message': message}
        except:
            raise ValueError("Error: " + response.text)
