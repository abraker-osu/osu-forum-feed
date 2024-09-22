import logging
import inspect
import warnings

from .Cmd import Cmd


from typing import TYPE_CHECKING, Callable
if TYPE_CHECKING:
    from core.BotBase import BotBase


class CommandProcessor():

    __instance = None

    def __new__(cls, *args, **kwargs):
        """
        Singleton

        NOTE: This relies on this to be initialized in ApiServer.py first
          before any further CommandProcessor() calls due to the passing
          of bot list.
        """
        if not cls.__instance:
            cls.__instance = super().__new__(cls)

        return cls.__instance


    def __init__(self, bots: "list[BotBase]" = None):
        if isinstance(bots, type(None)):
            return

        self.__logger = logging.getLogger(f'{__name__}')

        # Command dictionary
        # fmt:
        # {
        #     [cmd_name:str] : {
        #         'perm' : int,
        #         'help' : str,
        #         'exec' : Callable
        #     }
        # }
        self.__cmd_dict = {}

        # Load bot console commands
        for bot in bots:
            self.__logger.info(f'Loading {bot.name}...')

            # Get bot command dictionary. Also inject bot's cmd instance because it needs the self argument and idk of a better way to provide it
            bot_cmd_dict = bot.cmd.get_cmd_dict(f'{bot.name}.')
            for cmd_func in bot_cmd_dict.values():
                cmd_func['self'] = bot.cmd

                assert isinstance(cmd_func['self'], Cmd)
                assert isinstance(cmd_func['perm'], int)
                assert callable(cmd_func['exec'])

            self.__cmd_dict.update(bot_cmd_dict)
            self.__logger.info(
                f'\tLoaded commands: {list(bot_cmd_dict.keys())}\n'
                '============================'
            )


    @property
    def cmd_dict(self):
        return self.__cmd_dict.copy()


    def process_data(self, data: dict) -> dict:
        """
        Process a command data sent to the bot

        Parameters
        ----------
        data : dict
            Command data
            fmt:
            {
                'bot' : str,
                'cmd' : str,
                'args': tuple,
                'key' : int
            }

        Returns
        -------
        dict
            Command output
            fmt:
            {
                'src':      str
                'contents': str
            }
        """
        assert 'bot'  in data
        assert 'cmd'  in data
        assert 'args' in data
        assert 'key'  in data

        cmd_name = f'{data["bot"]}.{data["cmd"]}'
        if cmd_name not in self.__cmd_dict:
            self.__logger.debug(f'Invalid cmd: {data}')
            return Cmd.err('Command failed: No such command!')

        cmd_self:       Cmd = self.__cmd_dict[cmd_name]['self']
        exec_func: Callable = self.__cmd_dict[cmd_name]['exec']
        help_func: Callable = self.__cmd_dict[cmd_name]['help']
        cmd_perms: int      = self.__cmd_dict[cmd_name]['perm']

        args       = list(data['args'])
        cmd_params = inspect.signature(exec_func).parameters

        # Forfill the self argument by giving it the instance of the cmd object
        if 'self' in cmd_params:
            args.insert(0, cmd_self)

        # Validate the request. Note there are the following permission levels:
        #   Cmd.PERMISSION_PUBLIC  - Anyone and their grandmother is allowed to use the command
        #   Cmd.PERMISSION_SPECIAL - Anyone can use the command, but there are certain restrictions on a case-by-case basis, which are evaluated by validate_special_perm
        #   Cmd.PERMISSION_MOD     - Only users that are returned in the get_bot_moderators function are allowed to use the command
        #   Cmd.PERMISSION_ADMIN   - Only the bot owner (you) can use the command
        if not cmd_self.validate_request(( cmd_perms, data['key'] )):
            return Cmd.err(f'Insufficient permissions')

        # Check if sufficient num of args are provided
        num_param_req = len([ arg for arg in cmd_params.keys() if '=' not in str(cmd_params[arg]) ])
        if len(args) < num_param_req:
            self.__logger.debug(f'Not enough args for cmd: {cmd_name}; args: {args}')
            return help_func()

        if cmd_perms != Cmd.PERMISSION_PUBLIC:
            warnings.warn(f'Executing command "{cmd_name}" with permission level {cmd_perms}')

        # Run command function
        reply = exec_func(*args)

        if isinstance(reply, type(None)):
            warnings.warn('reply is None')
            return Cmd.err('Command failed: Bot did an oopsie daisy. Pls fix thx ^^;')

        return reply
