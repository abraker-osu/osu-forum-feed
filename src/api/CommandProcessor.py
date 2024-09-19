import logging
import inspect
import warnings

from .Cmd import Cmd


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.BotBase import BotBase


class CommandProcessor():

    __cmd_dict = {}

    def init(bots: "list[BotBase]"):
        CommandProcessor.__logger = logging.getLogger(f'{__name__}')

        # Load bot console commands
        for bot in bots:
            CommandProcessor.__logger.info(f'Loading {bot.name}...')

            # Get bot command dictionary. Also inject bot's cmd instance because it needs the self argument and idk of a better way to provide it
            bot_cmd_dict = bot.cmd.get_cmd_dict(f'{bot.name}.')
            for cmd_func in bot_cmd_dict.values():
                cmd_func['self'] = bot.cmd

                # Make sure the command has the cmd_key param if it requires higher user elevation to use
                cmd_params = inspect.signature(cmd_func['exec']).parameters
                if 'cmd_key' in cmd_params: continue

                if cmd_func['perm'] > Cmd.PERMISSION_PUBLIC:
                    CommandProcessor.__logger.warning(f'{cmd_func["exec"]} requires cmd_key parameter (Permission level {cmd_func["perm"]})')

            CommandProcessor.__cmd_dict.update(bot_cmd_dict)
            CommandProcessor.__logger.info(
                f'\tLoaded commands: {list(bot_cmd_dict.keys())}\n'
                '============================'
            )


    @staticmethod
    def process_data(data: dict) -> dict:
        """
        Process a command data sent to the bot

        Parameters
        ----------
        data : dict
            Command data

        Returns
        -------
        dict
            Command output
        """
        if not 'bot'  in data: CommandProcessor.__logger.info(f'Missing "bot"; cmd: {data}');  return Cmd.err('Invalid request format!')
        if not 'cmd'  in data: CommandProcessor.__logger.info(f'Missing "cmd"; cmd: {data}');  return Cmd.err('Invalid request format!')
        if not 'args' in data: CommandProcessor.__logger.info(f'Missing "args"; cmd: {data}'); return Cmd.err('Invalid request format!')
        if not 'key'  in data: CommandProcessor.__logger.info(f'Missing "key"; cmd: {data}');  return Cmd.err('Invalid request format!')

        cmd_name = f'{data["bot"]}.{data["cmd"]}'
        if cmd_name in CommandProcessor.__cmd_dict:
            reply = CommandProcessor.execute_cmd(cmd_name, data['key'], data['args'], CommandProcessor.__cmd_dict)
            if isinstance(reply, type(None)):
                warnings.warn('reply is None')
                return Cmd.err('Bot did an oopsie daisy. Pls fix thx ^^;')

            return reply

        CommandProcessor.__logger.info(f'Invalid command; cmd: {data}')
        return Cmd.err('No such command!')


    @staticmethod
    def execute_cmd(cmd_name: str, key: str, args: list | tuple, cmd_dict: dict) -> dict:
        """
        Execute a command

        Parameters
        ----------
        cmd_name : str
            Name of the command to execute
        key : str
            Command key
        args : tuple
            Command arguments
        cmd_dict : dict
            Command dictionary

        Returns
        -------
        dict
            Command output
        """
        args = list(args)
        CommandProcessor.__logger.info(f'key: {key}; cmd: {cmd_name} {args}')

        cmd_params    = inspect.signature(cmd_dict[cmd_name]['exec']).parameters
        num_param_req = len([ arg for arg in cmd_params.keys() if arg == str(cmd_params[arg]) ])

        # Forfill the self argument by giving it the instance of the cmd object
        if 'self' in cmd_params:
            args += [ cmd_dict[cmd_name]['self'] ]

        # Insert the command key as part of the command parameters if it's required
        if 'cmd_key' in cmd_params:
            args.insert(list(cmd_params.keys()).index('cmd_key'), (cmd_dict[cmd_name]['perm'], key))
        elif cmd_dict[cmd_name]['perm'] > Cmd.PERMISSION_PUBLIC:
            warnings.warn(f'{cmd_name} requires cmd_key parameter (Permission level {cmd_dict[cmd_name]["perm"]})')
            return Cmd.err('Something went wrong. Blame abraker.')

        # Check if sufficient num of args are provided
        if len(args) < num_param_req:
            return cmd_dict[cmd_name]['help']()

        # Take [:num_param_req + 1] to cutoff extra args
        try: return cmd_dict[cmd_name]['exec'](*args[:num_param_req + 1])
        except TypeError:
            return cmd_dict[cmd_name]['help']()


    @staticmethod
    @property
    def cmd_dict() -> dict:
        return CommandProcessor.__cmd_dict.copy()
