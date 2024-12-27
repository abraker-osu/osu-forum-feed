import requests
import logging
import warnings
import queue
import threading
import time

from misc.thread_enchanced import ThreadEnchanced

from .BotConfig import BotConfig


class DiscordClient():

    __instance = None

    __MAX_REQUEST_COUNT = 10
    __HANDLE_TIMEOUT    = 60  # 1 min

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

        cls.__lock = threading.Lock()
        cls.__queue = queue.Queue(maxsize=cls.__MAX_REQUEST_COUNT)
        cls.__thread_loop = ThreadEnchanced(
            target=cls.__loop, args=( threading.Event(), threading.Event() ),
            daemon=True
        )
        cls.__thread_loop.start()

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
            self.__logger.debug(f'Queuing data for route {route}')
            try: self.__queue.put( ( route, data ) )
            except queue.Full:
                warnings.warn(f'DiscordClient: Queue is full', UserWarning, source='DiscordClient')
                return


    @staticmethod
    def __loop(target_event: threading.Event, thread_event: threading.Event):
        self = DiscordClient()

        while True:
            target_event.set()
            if thread_event.is_set():
                self.__logger.debug(f'Got stop signal for thread {threading.current_thread().name}')
                target_event.set()
                return

            try: route, data = self.__queue.get(block=True, timeout=1)
            except queue.Empty:
                continue

            self.__send_data(f'http://127.0.0.1:{self.__port}/{route}', data)


    @staticmethod
    def __send_data(url: str, data: dict):
        time_start = time.time()

        while time.time() - time_start < DiscordClient.__HANDLE_TIMEOUT:
            try:
                response = DiscordClient.__session.post(url, json=data)
                break
            except ( requests.exceptions.Timeout, requests.exceptions.ConnectionError ):
                warnings.warn(f'DiscordClient: No Discord feed server reply! Retrying in 10 second(s)...', UserWarning, source='DiscordClient')
                time.sleep(10)
                continue

        if response.status_code != 200:
            warnings.warn(f'DiscordClient: Unable to make request: {response.status_code}', UserWarning, source='DiscordClient')
