import time
import warnings

from core.BotBase import BotBase
from core.parser.Post import Post
from core.ForumMonitor import ForumMonitor

from api import Cmd
from api import CommandProcessor

from misc import Utils



class AdminBot(BotBase):
    """
    Bot responsible for managing the core.
    """

    def __init__(self):
        BotBase.__init__(self, self.BotCmd, self.__class__.__name__, enable=False)


    def post_init(self):
        pass


    def process_data(self, forum_data: Post):
        return {}


    class BotCmd(Cmd):

        def __init__(self, obj: BotBase):
            Cmd.__init__(self, obj)


        def get_bot_moderators(self):
            return []


        def validate_special_perm(self, requestor_id, access_id):
            return False


        @Cmd.help(
        perm = Cmd.PERMISSION_PUBLIC,
        info = 'If no arguments are provided, lists all available bot commands. Otherwise, pring the indicated command\'s help info.',
        args = {
            'cmd_name' : Cmd.arg(str, True, 'Name of the command to show help info for')
        })
        def cmd_help(self, cmd_key, cmd_name=None):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            if isinstance(cmd_name, type(None)):
                bot_cmds = "\n".join(list(CommandProcessor.cmd_dict.keys()))
                return Cmd.ok(
                    'List of bot commands:\n'
                    f'{bot_cmds}'
                )

            if cmd_name in CommandProcessor.cmd_dict:
                reply = CommandProcessor.cmd_dict[cmd_name]['help']()
                if reply == None:
                    warnings.warn('Reply is None')
                    Cmd.err('Please tell abraker of his incompetence')

                return reply

            return Cmd.err(f'No such command: "{cmd_name}"')


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Kills the entire thing',
        args = {
        })
        def cmd_kill(self, cmd_key):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            ForumMonitor.runtime_quit = True
            return Cmd.ok()


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Shows a log of recently recorded events',
        args = {
            'log' : Cmd.arg([str], False, 'Log of which bot to display'),
            'bot' : Cmd.arg([bool], True, 'Is it a bot log?')
        })
        def cmd_show_log(self, cmd_key, log, bot=True):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            if '/' in log or '\\' in log:
                return Cmd.err('Invalid log')

            if bot == True:
                log = f'bots/{log}'

            print(log, bot, f'logs/{log}.log')

            try:    return Cmd.ok(Utils.tail(10, f'logs/{log}.log'))
            except: return Cmd.err('Invalid log')


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Shows what latest post and thread the forum monitor is on',
        args = {
        })
        def cmd_latest_post_thread(self, cmd_key):
            """
            Shows what latest post and thread the forum monitor is on
            """
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            return Cmd.ok(f'Latest post: {ForumMonitor.get_latest_post()}')


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Sets the latest post processed by Forum Monitor',
        args = {
        })
        def cmd_set_latest_post(self, cmd_key, latest_post):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            try: latest_post = int(latest_post)
            except ValueError:
                return Cmd.err(f'Invalid post id')

            ForumMonitor.set_enable(ForumMonitor.NEW_POST, False)
            while ForumMonitor.get_status(ForumMonitor.NEW_POST) == True:
                time.sleep(0.1)

            ForumMonitor.set_latest_post(latest_post)
            ForumMonitor.set_enable(ForumMonitor.NEW_POST, True)

            return Cmd.ok()


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Shows when the core started running',
        args = {
        })
        def cmd_time_run(self, cmd_key):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            return Cmd.err('TODO')


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Lists available bots and their statuses',
        args = {
        })
        def cmd_list_bots(self, cmd_key):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            bots: list[BotBase] = ForumMonitor.get_bot(None)
            text = [ f'{" [ Enabled ]" if bot.is_enabled else "[ Disabled ]"} {bot.name}' for bot in bots ]
            return Cmd.ok('\n'.join(text))


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Disables the specified bot',
        args = {
            'bot_name' : Cmd.arg(str, False, 'Bot name')
        })
        def cmd_disable_bot(self, cmd_key, bot_name):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            try: bot: BotBase = ForumMonitor.get_bot(bot_name)
            except KeyError:
                return Cmd.err('No such bot')

            bot.disable()
            return Cmd.ok()


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Enables the specified bot',
        args = {
            'bot' : Cmd.arg(str, False, 'Bot name')
        })
        def cmd_enable_bot(self, cmd_key, bot_name):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            try: bot: BotBase = ForumMonitor.get_bot(bot_name)
            except KeyError:
                return Cmd.err('No such bot')

            bot.enable()
            return Cmd.ok()