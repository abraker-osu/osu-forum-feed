from typing import Union

import requests
import time
import logging

from core import BotBase
from core import Cmd

from bots.ForumFeedBotCore import DiscordClient
from core import Topic, Post


class OTFeedBot(BotBase):

    def __init__(self, botcore):
        BotBase.__init__(self, botcore, self.BotCmd, self.__class__.__name__, enable = True)


    def post_init(self):
        pass


    def filter_data(self, post: Post):
        return int(post.topic.subforum_id) == 52


    def process_data(self, post: Post):
        self.logger.debug(f'New post: https://osu.ppy.sh/forum/p/{post.id}')

        # Get previous post's timestamp
        prev_post = post.prev_post
        if prev_post == None:
            prev_post_date = post.date
        else:
            prev_post_date = prev_post.date

        data = {
            'subforum_id'    : post.topic.subforum_id,
            'subforum_name'  : post.topic.subforum_name,
            'post_date'      : str(post.date),
            'prev_post_date' : str(prev_post_date),
            'first_post_id'  : post.topic.first_post.id,
            'thread_title'   : post.topic.name,
            'post_id'        : str(post.id),
            'first_post_id'  : post.topic.first_post.id,
            'username'       : post.creator.name,
            'user_id'        : post.creator.id,
            'avatar_url'     : post.creator.avatar,
            'contents'       : post.content_markdown
        }

        self.__send_data(self.logger, 'post', data)


    def __send_data(self, logger: logging.Logger, route: str, data: "dict[str, str]"):
        handle_rate = self.get_cfg('Core', 'rate_post_min')

        while True:
            try:
                DiscordClient.request(self.get_cfg('ForumFeedBot', 'discord_bot_port'), route, data)
                break
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                logger.warn(f'No Discord feed server reply! Retrying in {handle_rate} second(s)...')
                time.sleep(handle_rate)

                # 1 hour max
                handle_rate = min(3600, handle_rate + 10)
                continue


    class BotCmd(Cmd):

        # obj is what the commands interface with
        def __init__(self, logger, obj):
            self.logger = logger
            self.obj    = obj


        # This is one of the four function that are required to be defined in the derived class and serves to provide
        # a list of users who are allowed to use commands up to Cmd.PERMISSION_MOD level
        def get_bot_moderators(self):
            return []


        # This is one of the four function that are required to be defined in the derived class and serves to check
        # whether the user who requested the command (requestor_id) can use the command based on whatever conditions
        # specified in args. This might be the user id they are trying to access, their requestor id's specific
        # status, and so on.
        def validate_special_perm(self, requestor_id, args):
            return False


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Prints the about text for ForumFeedBot',
        args = {
        })
        def cmd_about(self, cmd_key):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            return Cmd.ok('Forwards forum posts to a discord channel')


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Prints the help text for ForumFeedBot',
        args = {
        })
        def cmd_help(self, cmd_key):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            return Cmd.ok('TODO')
