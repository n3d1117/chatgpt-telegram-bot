import datetime
import json
import logging
import os
import uuid

import requests


class ChatGPT3Bot:
    def __init__(self, config):
        self.config = config
        self.check_access_token()
        self.parent_id = self.generate_uuid()
        self.conversation_id = None

    def check_access_token(self, force_refresh=False):
        filename = 'access_token.json'

        def fetch_access_token():
            logging.info("Fetching access token...")
            response = self.extract_openai_access_token(self.config['openai_session_token'])
            if response:
                self.access_token = response['access_token']
                with open(filename, 'w') as f:
                    f.write(json.dumps(response))
            else:
                raise ValueError("Error: Unable to extract access token")

        if force_refresh or not os.path.exists(filename):
            fetch_access_token()
        else:
            with open(filename, 'r') as f:
                response = json.loads(f.read())
                if datetime.datetime.strptime(response["expires"], '%Y-%m-%d %H:%M:%S') < datetime.datetime.now():
                    logging.info("Access token expired, re-fetching...")
                    fetch_access_token()
                else:
                    self.access_token = response['access_token']

    # Credits: https://github.com/acheong08/ChatGPT
    def extract_openai_access_token(self, session_token) -> json:
        s = requests.Session()
        s.cookies.set("__Secure-next-auth.session-token", session_token)
        response = s.get("https://chat.openai.com/api/auth/session")
        response_json = response.json()
        expiration_date = datetime.datetime.now() + datetime.timedelta(hours=1)
        return {
            'access_token': response_json['accessToken'],
            'expires': expiration_date.strftime('%Y-%m-%d %H:%M:%S')
        }

    def generate_uuid(self) -> str:
        return str(uuid.uuid4())

    # Credits: https://github.com/acheong08/ChatGPT
    def get_chat_response(self, prompt, on_force_refresh=False) -> json:
        self.check_access_token()

        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer " + self.access_token,
            "Content-Type": "application/json"
        }
        data = {
            "action": "next",
            "messages": [{
                "id": self.generate_uuid(),
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
            if not on_force_refresh and response.status_code == 500:
                self.check_access_token(force_refresh=True)
                return self.get_chat_response(prompt, on_force_refresh=True)
            else:
                response = response.text.splitlines()[-4][6:]
                response = json.loads(response)
                self.parent_id = response["message"]["id"]
                self.conversation_id = response["conversation_id"]
                message = response["message"]["content"]["parts"][0]
                return {'message': message}
        except:
            raise ValueError("Error: " + response.text)

    def reset(self):
        self.conversation_id = None
        self.parent_id = self.generate_uuid()
