from typing import Union

from core import BotBase
from core import Cmd
from core import Post, Topic


class OTBot(BotBase):

    def __init__(self, core):
        BotBase.__init__(self, core, self.BotCmd, self.__class__.__name__, enable = True)
        self.__subforum_id = '52'


    def post_init(self):
        pass


    def filter_data(self, forum_data: Union[Post, Topic]):
        return (forum_data.topic.subforum_id == self.__subforum_id)


    def process_data(self, forum_data: Union[Post, Topic]):
        self.logger.debug('Bot read')

        if not isinstance(forum_data, Post):
            return

        self.logger.info(f'Found OT post by: {forum_data.creator.name} in thread: {forum_data.topic.name}')

        data = {}
        if forum_data.creator.name == 'abraker':
            content = forum_data.contents_text
            if content.find('owh') != -1:
                data['post_id']    = forum_data.id
                data['post_count'] = int(forum_data.topic.post_count)

        if 'post_id' not in data:
            return

        self.logger.info('Writing post count to post...')
        self.edit_post(str(data['post_id']), '\n\n edit: ' + str(data['post_count']), append=True)


    class BotCmd(Cmd):

        def __init__(self, logger, obj):
            self.logger = logger
            self.obj    = obj


        def get_bot_moderators(self):
            return []


        def validate_special_perm(self, requestor_id, access_id):
            return False


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Prints the about text for OTBot',
        args = {
        })
        def cmd_about(self, cmd_key):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            return Cmd.ok('This bot is just a testing bot for more complicated stuff')


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Prints the help text for OTBot',
        args = {
        })
        def cmd_help(self, cmd_key):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            return Cmd.ok('This bot goes through off-topic\'s threads and posts')

