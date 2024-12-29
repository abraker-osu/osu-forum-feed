import logging
import queue
import threading

from .parser import Post
from misc.thread_enchanced import ThreadEnchanced

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from api.Cmd import Cmd


class BotBase:

    def __init__(self, cmd: "type[Cmd]", name: str, enable: bool):
        self.logger    = logging.getLogger(f'bots.{name}')
        self.__enable  = enable
        self.__name    = name
        self.__bot_cmd = cmd(self)

        self.__post_queue = queue.Queue()
        self.__bot_thread = ThreadEnchanced(
            target=self.__loop, args=( threading.Event(), threading.Event() ),
            daemon=True
        )
        self.__bot_thread.start()


    def post_init(self):
        raise NotImplementedError()


    @property
    def cmd(self) -> "Cmd":
        return self.__bot_cmd


    @property
    def name(self) -> str:
        return self.__name


    def enable(self) -> None:
        """
        Enable the bot. This will allow the bot to receive new post events.
        """
        self.__enable = True



    def disable(self) -> None:
        """
        Disable the bot. This will prevent the bot from receiving new post events.
        """
        self.__enable = False


    @property
    def is_enabled(self) -> bool:
        return self.__enable


    def event(self, forum_data: Post):
        """
        To be called for each new post

        Parameters
        ----------
        forum_data : Post
            The `Post` object to process.
        """
        if not self.__enable:
            return

        if not self.filter_data(forum_data):
            self.logger.debug(f'Filtered out post {forum_data.id} in {forum_data.topic.subforum_name}')
            return

        self.logger.debug(f'Queuing post {forum_data.id} in {forum_data.topic.subforum_name}')
        self.__post_queue.put(forum_data)


    def filter_data(self, forum_data: Post) -> bool:
        """
        Bot filter criteria. By default, it doesn't filter anything.
        Reimplement this method if it's desired to filter posts.

        Not meant to be used publically.

        Parameters
        ----------
        forum_data : Post
            The `Post` object to filter.

        Returns
        -------
        bool
            Whether the `Post` object should be filtered or not.
        """
        return True


    def process_data(self, forum_data: Post) -> None:
        """
        Processes the given forum data; used by the bot module to process
        data. This method should be overridden in a child class to do
        something with the forum data.

        Not meant to be used publically.

        Parameters
        ----------
        forum_data : Post
            The `Post` object to process.

        Raises
        ------
        NotImplementedError
            If this method is not implemented in the child class.
        """
        raise NotImplementedError('process_data method not implemented')


    def __loop(self, target_event: threading.Event, thread_event: threading.Event):
        while True:
            target_event.set()
            if thread_event.is_set():
                self.logger.debug(f'Got stop signal for thread {threading.current_thread().name}')
                target_event.set()
                return

            try: post = self.__post_queue.get(block=True, timeout=1)
            except queue.Empty:
                continue

            assert isinstance(post, Post)

            self.logger.debug(f'Processing post {post.id}')
            self.process_data(post)
