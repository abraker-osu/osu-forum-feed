import requests
import logging
import warnings
import threading
import time

from misc.thread_enchanced import ThreadEnchanced

from .BotConfig import BotConfig


class DiscordClient():

    __instance = None

    __MAX_THREAD_COUNT = 10
    __THREAD_TIMEOUT   = 60

    def __new__(cls, *args, **kwargs):
        """
        Singleton
        """
        if cls.__instance is not None:
            return cls.__instance

        cls.__instance = super().__new__(cls, *args, **kwargs)

        cls.__session          = requests.session()
        cls.__logger           = logging.getLogger(__name__)
        cls.__port: int        = BotConfig['Core']['discord_bot_port']
        cls.__handle_rate: int = BotConfig['Core']['rate_post_min']

        cls.__lock = threading.Lock()
        cls.__thread_pool: list[ThreadEnchanced] = []

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
        self.__logger.debug(f'Performing request: {route} {data}')

        with self.__lock:
            # Check for finished requests
            for thread in self.__thread_pool.copy():
                if not thread.is_alive():
                    self.__logger.debug(f'Thread {thread.name} has finished; removing...')
                    self.__thread_pool.remove(thread)
                    continue

                if thread.runtime > self.__THREAD_TIMEOUT:
                    self.__logger.warning(f'DiscordClient: Thread {thread.name} timed out')
                    thread.stop()
                    self.__thread_pool.remove(thread)

            # Check if there are too many pending requests
            if len(self.__thread_pool) > self.__MAX_THREAD_COUNT:
                warnings.warn(f'DiscordClient: Too many pending requests (num threads: {len(self.__thread_pool)})')
                return

            # Execute request
            thread = ThreadEnchanced(
                target=self.__send_data, args=(threading.Event(), threading.Event(), f'http://127.0.0.1:{self.__port}/{route}', data),
                daemon=True
            )
            thread.start()
            self.__thread_pool.append(thread)
            self.__logger.debug(f'Created thread {thread.name} | Num threads: {len(self.__thread_pool)}')


    @staticmethod
    def __send_data(target_event: threading.Event, thread_event: threading.Event, url: str, data: dict):
        target_event.set()
        handle_rate = DiscordClient.__handle_rate

        while True:
            if thread_event.is_set():
                DiscordClient.__logger.debug(f'Got stop signal for thread {threading.current_thread().name}')
                target_event.set()
                return

            try:
                response = DiscordClient.__session.post(url, json=data)
                break
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                warnings.warn(f'No Discord feed server reply! Retrying in {handle_rate} second(s)...')
                time.sleep(handle_rate)

                # 1 hour max
                handle_rate = min(3600, handle_rate + 10)
                continue

        if response.status_code != 200:
            warnings.warn(f'DiscordClient: Unable to make request: {response.status_code}')
