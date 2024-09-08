import requests
import logging
import json


class DiscordClient():

    __session = requests.session()
    __logger  = logging.getLogger(__name__)

    @staticmethod
    def request(port: int, route: str, data: dict):
        response = DiscordClient.__session.post(f'http://127.0.0.1:{port}/{route}', json=data)
        DiscordClient.__logger.info(response)

        # Check if it's HTTP OK
        if response.status_code != 200:
            raise Exception(f'Error {response.status_code}')

        data = json.loads(response.text)
        DiscordClient.__logger.debug(data)
