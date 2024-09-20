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

                # Make sure the command has the `cmd_key` param if it requires higher user elevation to use
                cmd_params = inspect.signature(cmd_func['exec']).parameters
                if 'cmd_key' in cmd_params:
                    continue

                if cmd_func['perm'] > Cmd.PERMISSION_PUBLIC:
                    self.__logger.warning(f'{cmd_func["exec"]} requires "cmd_key" parameter (Permission level {cmd_func["perm"]})')

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
        """
        assert 'bot'  in data
        assert 'cmd'  in data
        assert 'args' in data
        assert 'key'  in data

        cmd_name = f'{data["bot"]}.{data["cmd"]}'
        if cmd_name not in self.__cmd_dict:
            self.__logger.debug(f'Invalid cmd: {data}')
            return Cmd.err('Command failed: No such command!')

        self.__logger.info(f'Executing cmd: {data}')
        reply = self.__execute_cmd(cmd_name, data['key'], data['args'])
        if isinstance(reply, type(None)):
            warnings.warn('reply is None')
            return Cmd.err('Command failed: Bot did an oopsie daisy. Pls fix thx ^^;')

        return reply


    def __execute_cmd(self, cmd_name: str, key: int, args: list | tuple) -> dict:
        """
        Execute a command

        Parameters
        ----------
        cmd_name : str
            Name of the command to execute
        key : int
            Command key
        args : tuple
            Command arguments

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
        exec_func: Callable = self.__cmd_dict[cmd_name]['exec']
        help_func: Callable = self.__cmd_dict[cmd_name]['help']
        cmd_perms: int      = self.__cmd_dict[cmd_name]['perm']

        args          = list(args)
        cmd_params    = inspect.signature(exec_func).parameters
        num_param_req = len([ arg for arg in cmd_params.keys() if arg == str(cmd_params[arg]) ])

        # Forfill the self argument by giving it the instance of the cmd object
        if 'self' in cmd_params:
            args.insert(0, self.__cmd_dict[cmd_name]['self'])

        # Insert the command key as part of the command parameters if it's required
        if 'cmd_key' in cmd_params:
            idx = list(cmd_params.keys()).index('cmd_key')
            args.insert(idx, ( cmd_perms, key ))
        elif cmd_perms > Cmd.PERMISSION_PUBLIC:
            warnings.warn(f'{cmd_name} requires cmd_key parameter (Permission level {cmd_perms})')
            return Cmd.err('Something went wrong. Blame abraker.')

        # Check if sufficient num of args are provided
        if len(args) < num_param_req:
            self.__logger.debug(f'Not enough args for cmd: {cmd_name}; args: {args}')
            return help_func()

        # Take [:num_param_req + 1] to cutoff extra args
        return exec_func(*args)
        # try: return exec_func(*args)
        # except TypeError as e:
        #     self.__logger.debug(
        #         f'Invalid args for cmd: {cmd_name} ({e})\n'
        #         f'\targs: {args}\n'
        #         f'\texpected: {cmd_params}'
        #     )
        #     return help_func()
