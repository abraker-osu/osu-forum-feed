import logging
import requests

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from .console_framework import Cmd
    from .ForumMonitor import ForumMonitor
    from .parser import Post, Topic


class BotBase:

    def __init__(self, core: "ForumMonitor", cmd: "Cmd", name: str, enable: bool):
        self.logger    = logging.getLogger(f'bots/{name}')
        self.__core    = core
        self.__enable  = enable
        self.__name    = name
        self.__bot_cmd = cmd(self.logger, self)


    def post_init(self):
        raise NotImplementedError()


    def enable(self):
        self.__enable = True


    def disable(self):
        self.__enable = False


    def is_enabled(self) -> bool:
        return self.__enable


    def event(self, forum_data: "Post"):
        if not self.__enable:
            return

        if not self.filter_data(forum_data):
            return

        try: self.process_data(forum_data)
        except Exception as e:
            self.logger.warning(repr(e))
            return


    def filter_data(self, forum_data: "Post") -> bool:
        return True


    # process_data is meant to be used by the bot to do whatever it wants with the data it gets
    def process_data(self, forum_data: "Post"):
        msg = 'process_data method not implemented'
        self.logger.error(msg)
        raise NotImplementedError(msg)


    def get_cfg(self, src: str, key: str):
        return self.__core.get_cfg(src, key)


    def get_name(self) -> str:
        return self.__name


    def edit_post(self, post_id: int | str, new_content: str, append: bool = False):
        self.__core.edit_post(post_id, new_content, append)


    def get_post(self, post_id: int | str, page: requests.Response | type[None] = None) -> "Post":
        self.__core.get_post(post_id, page)


    def get_prev_post(self, ref_post: "Post") -> "Optional[Post]":
        self.__core.get_prev_post(ref_post)


    def get_next_post(self, ref_post: "Post") -> "Optional[Post]":
        self.__core.get_next_post(ref_post)
