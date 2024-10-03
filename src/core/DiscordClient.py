import requests
import logging

from .BotConfig import BotConfig


class DiscordClient():

    __instance = None

    def __new__(cls, *args, **kwargs):
        """
        Singleton
        """
        if not cls.__instance:
            cls.__instance = super().__new__(cls, *args, **kwargs)

        cls.__session = requests.session()
        cls.__logger  = logging.getLogger(__name__)
        cls.__port    = BotConfig['Core']['discord_bot_port']

        return cls.__instance

    @staticmethod
    def request(route: str, data: dict):
        """
        fmt data:
            {
                'src':      str
                'contents': str
            }
        """
        self = DiscordClient()
        response = self.__session.post(f'http://127.0.0.1:{self.__port}/{route}', json=data)

        # Check if it's HTTP OK
        if response.status_code != 200:
            raise Exception(f'Error {response.status_code}')
