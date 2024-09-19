import logging

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from api import Cmd
    from .parser import Post


class BotBase:

    def __init__(self, cmd: "type[Cmd]", name: str, enable: bool):
        self.logger    = logging.getLogger(f'bots.{name}')
        self.__enable  = enable
        self.__name    = name
        self.__bot_cmd = cmd(self)


    def post_init(self):
        raise NotImplementedError()

    @property
    def cmd(self) -> "Cmd":
        return self.__bot_cmd


    @property
    def name(self) -> str:
        return self.__name


    def enable(self):
        self.__enable = True


    def disable(self):
        self.__enable = False


    @property
    def is_enabled(self) -> bool:
        return self.__enable


    def event(self, forum_data: "Post"):
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
            return

        try: self.process_data(forum_data)
        except Exception as e:
            self.logger.warning(repr(e))
            return


    def filter_data(self, forum_data: "Post") -> bool:
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


    def process_data(self, forum_data: "Post") -> None:
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
        msg = 'process_data method not implemented'
        self.logger.error(msg)
        raise NotImplementedError(msg)
