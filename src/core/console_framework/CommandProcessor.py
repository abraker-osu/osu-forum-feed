import time
import logging
import inspect

from core.console_framework import Cmd
from core import ForumMonitor
from core import Utils
from core import BotBase


class CommandProcessor():

    _init        = False
    _logger      = None
    _cmd_dict    = {}

    @staticmethod
    def init(bots: "list[BotBase]"):
        CommandProcessor._logger = logging.getLogger(__class__.__name__)

        # Load native commands
        CommandProcessor._logger.info('Loading admin bot commands...')

        native_cmd = CommandProcessor.Core(CommandProcessor._logger, CommandProcessor, bots)
        cmd_dict   = native_cmd.get_cmd_dict('Core.')

        # Inject bot's cmd instance because it needs the self argument and idk of a better way to provide it
        for cmd_func in cmd_dict.values():
            cmd_func['self'] = native_cmd

        CommandProcessor._cmd_dict = { **CommandProcessor._cmd_dict, **cmd_dict }
        CommandProcessor._logger.info('\tLoaded commands: ' + str(list(cmd_dict.keys())) + '\n============================')

        # Load bot admin console commands
        for bot in bots:
            bot_name = bot.get_name()
            CommandProcessor._logger.info('Loading ' + bot_name + '...')

            # Get bot command dictionary. Also inject bot's cmd instance because it needs the self argument and idk of a better way to provide it
            bot_cmd_dict = bot._bot_cmd.get_cmd_dict(bot_name + '.')
            for cmd_func in bot_cmd_dict.values():
                cmd_func['self'] = bot._bot_cmd

                # Make sure the command has the cmd_key param if it requires higher user elevation to use
                cmd_params = inspect.signature(cmd_func['exec']).parameters
                if 'cmd_key' in cmd_params: continue

                if cmd_func['perm'] > Cmd.PERMISSION_PUBLIC:
                    CommandProcessor._logger.warn(f'{cmd_func["exec"]} requires cmd_key parameter (Permission level {cmd_func["perm"]})')

            CommandProcessor._cmd_dict = { **CommandProcessor._cmd_dict, **bot_cmd_dict }
            CommandProcessor._logger.info('\tLoaded commands: ' + str(list(bot_cmd_dict.keys())) + '\n============================')

        CommandProcessor._init = True


    @staticmethod
    def process_data(data):
        if not 'bot'  in data: CommandProcessor._logger.info(f'Missing "bot"; cmd: {data}');  return Cmd.err('Invalid request format!')
        if not 'cmd'  in data: CommandProcessor._logger.info(f'Missing "cmd"; cmd: {data}');  return Cmd.err('Invalid request format!')
        if not 'args' in data: CommandProcessor._logger.info(f'Missing "args"; cmd: {data}'); return Cmd.err('Invalid request format!')
        if not 'key'  in data: CommandProcessor._logger.info(f'Missing "key"; cmd: {data}');  return Cmd.err('Invalid request format!')

        cmd_name = str(data['bot']) + '.' + str(data['cmd'])
        if cmd_name in CommandProcessor._cmd_dict:
            reply = CommandProcessor.execute_cmd(cmd_name, data['key'], data['args'], CommandProcessor._cmd_dict)
            if reply == None: return Cmd.err('Please tell abraker of his incompetence')
            else:             return reply

        CommandProcessor._logger.info(f'Invalid command; cmd: {data}')
        return Cmd.err('No such command!')


    @staticmethod
    def execute_cmd(cmd_name: str, key: str, args: tuple, cmd_dict: dict):
        CommandProcessor._logger.info(f'key: {key}; cmd: {cmd_name} {args}')

        cmd_params    = inspect.signature(cmd_dict[cmd_name]['exec']).parameters
        num_param_req = len([ arg for arg in cmd_params.keys() if arg == str(cmd_params[arg]) ])

        # Forfill the self argument by giving it the instance of the cmd object
        if 'self' in cmd_params: args = [ cmd_dict[cmd_name]['self'] ] + args

        # Insert the command key as part of the command parameters if it's required
        if 'cmd_key' in cmd_params: args.insert(list(cmd_params.keys()).index('cmd_key'), (cmd_dict[cmd_name]['perm'], key))
        elif cmd_dict[cmd_name]['perm'] > Cmd.PERMISSION_PUBLIC:
            CommandProcessor._logger.error(f'{cmd_name} requires cmd_key parameter (Permission level {cmd_dict[cmd_name]["perm"]})')
            return Cmd.err('Something went wrong. Blame abraker.')

        if len(args) < num_param_req:
            return cmd_dict[cmd_name]['help']()

        # Take [:num_param_req + 1] to cutoff extra args
        try: return cmd_dict[cmd_name]['exec'](*args[:num_param_req + 1])
        except TypeError: return cmd_dict[cmd_name]['help']()


    class Core(Cmd):

        def __init__(self, logger: logging.Logger, obj: ForumMonitor, bots: "list[BotBase]"):
            self.logger = logger
            self.obj    = obj
            self.bots   = bots


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

            if not cmd_name:
                return Cmd.ok('List of bot commands:\n' + '\n'.join(list(CommandProcessor._cmd_dict.keys())))

            if cmd_name in CommandProcessor._cmd_dict:
                reply = CommandProcessor._cmd_dict[cmd_name]['help']()
                if reply == None: Cmd.err('Please tell abraker of his incompetence')

                return reply

            return Cmd.err('No such command "' + cmd_name + '"')


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Kills the entire thing',
        args = {
        })
        def cmd_kill(self, cmd_key):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            self.obj.runtime_quit = True
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

            if '/' in log or '\\' in log: return Cmd.err('Invalid log')
            if bot == True: log = 'bots/' + log

            print(log, bot, f'logs/{log}.log')

            try:    return Cmd.ok(Utils.tail(10, f'logs/{log}.log'))
            except: return Cmd.err('Invalid log')


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Shows what latest post and thread the forum monitor is on',
        args = {
        })
        def cmd_latest_post_thread(self, cmd_key):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            return Cmd.ok(f'Latest post: {self.obj.get_latest_post()}')


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Sets the latest post processed by Forum Monitor',
        args = {
        })
        def cmd_set_latest_post(self, cmd_key, latest_post):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            try: latest_post = int(latest_post)
            except ValueError: return Cmd.err(f'Invalid post id')

            self.obj.set_enable(self.obj.NEW_POST, False)
            while(self.obj.get_status(self.obj.NEW_POST) == True): time.sleep(0.1)

            self.obj.set_latest_post(latest_post)
            self.obj.set_enable(self.obj.NEW_POST, True)

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

            text = [ f'{" [ Enabled ]" if bot.is_enabled() else "[ Disabled ]"} {bot.get_name()}' for bot in self.bots ]
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

            bot = [ bot for bot in self.bots if bot.get_name() == bot_name ]
            if len(bot) == 0: return Cmd.err('No such bot')

            bot[0].disable()
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

            bot = [ bot for bot in self.bots if bot.get_name() == bot_name ]
            if len(bot) == 0: Cmd.err('No such bot')

            bot[0].enable()
            return Cmd.ok()
