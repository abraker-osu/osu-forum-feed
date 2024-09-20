from core.SessionMgrV2 import SessionMgrV2
from core.BotBase import BotBase

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.parser.Post import Post

from api.Cmd import Cmd


class OTBot(BotBase):

    def __init__(self):
        BotBase.__init__(self, OTBot.BotCmd, self.__class__.__name__, enable = True)


    def post_init(self):
        pass


    def filter_data(self, post: "Post"):
        return int(post.topic.subforum_id) == 52


    def process_data(self, post: "Post"):
        self.logger.info(f'Found OT post by: {post.creator.name} in thread: {post.topic.name}')

        data = {}
        if post.creator.name == 'abraker':
            content = post.contents_text
            if content.find('owh') != -1:
                data['post_id']    = post.id
                data['post_count'] = int(post.topic.post_count)

        if 'post_id' not in data:
            return

        self.logger.info('Writing post count to post...')
        SessionMgrV2.edit_post(str(data['post_id']), '\n\n edit: ' + str(data['post_count']), append=True)


    class BotCmd(Cmd):

        def __init__(self, obj: BotBase):
            Cmd.__init__(self, obj)

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

