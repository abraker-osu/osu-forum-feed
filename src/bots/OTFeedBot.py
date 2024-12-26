from core.BotBase import BotBase
from core.DiscordClient import DiscordClient
from core.parser.Post import Post

from api.Cmd import Cmd


class OTFeedBot(BotBase):

    def __init__(self):
        BotBase.__init__(self, self.BotCmd, self.__class__.__name__, enable = True)


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
        DiscordClient.request('/osu/post', data)


    class BotCmd(Cmd):

        # obj is what the commands interface with
        def __init__(self, obj):
            Cmd.__init__(self, obj)


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
        def cmd_about(self):
            return Cmd.ok('Forwards forum posts to a discord channel')


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Prints the help text for ForumFeedBot',
        args = {
        })
        def cmd_help(self):
            return Cmd.ok('TODO')
