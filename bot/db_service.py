import logging

import json
import psycopg2
from psycopg2.extras import DictCursor


class DbService:
    def __init__(self, config: dict):
        self.connection = psycopg2.connect(
            dbname=config['db_name'],
            user=config['db_user'],
            host=config['db_host'],
            password=config['db_pass'],
            port=config['db_port'])

    # Insert prompt
    def create_prompt(self, text):
        connection = self.connection
        cursor = connection.cursor()
        try:
            cursor.execute("INSERT INTO prompt (text) VALUES (%s) RETURNING id;", (text,))
            prompt_id = cursor.fetchone()[0]
            connection.commit()
            logging.info("Inserted prompt with id %s", prompt_id)
            return prompt_id
        except Exception as e:
            logging.warning("Insert error: ", e)
            connection.rollback()
        finally:
            cursor.close()

    # Select all prompts
    def get_all_prompts(self):
        connection = self.connection
        cursor = connection.cursor(cursor_factory=DictCursor)
        try:
            cursor.execute("SELECT * FROM prompt;")
            prompts = cursor.fetchall()
            decoded_prompts = decode_prompt_list(prompts)

            logging.info("All prompts " + str(decoded_prompts))
            return decoded_prompts
        except Exception as e:
            logging.warning(f'Error while getting all prompts: {e}')
        finally:
            cursor.close()

    # Select prompt by id
    def get_prompt_by_id(self, id):
        connection = self.connection
        cursor = connection.cursor(cursor_factory=DictCursor)
        try:
            cursor.execute("SELECT * FROM prompt WHERE id = %s;", (id,))
            prompt = cursor.fetchone()
            if prompt is None:
                raise RuntimeError(f'Prompt with {id} not found')
            return decode_prompt(prompt)
        except Exception as e:
            logging.warning(f'Error while getting prompt: {id}. {e}')
        finally:
            cursor.close()

    def __del__(self):
        self.connection.close()


def decode_prompt_list(prompts):
    decoded_prompts = []
    for prompt in prompts:
        decoded_prompts.append(decode_prompt(prompt))
    return decoded_prompts


def decode_prompt(prompt):
    return [item if isinstance(item, int) else json.loads(f'"{item}"') for item in prompt]
