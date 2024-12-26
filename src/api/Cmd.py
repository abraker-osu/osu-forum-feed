from typing import Optional, Callable
import logging
import warnings

from core.BotConfig import BotConfig
from core.BotBase import BotBase


class Cmd():
    """
    Class used by bot modules to implement API commands
    for controlling the bot.
    """

    PERMISSION_PUBLIC  = 0  # Anyone can use this command
    PERMISSION_SPECIAL = 1  # Special roles can use this command + mod + admin
    PERMISSION_MOD     = 2  # Mods roles can use this command + admin
    PERMISSION_ADMIN   = 3  # Only admin is able to use this command

    def __init__(self, obj: BotBase):
        assert isinstance(obj, BotBase)

        self.__logger = logging.getLogger(f'{__name__}.{obj.name}')
        self.obj = obj

        if len(self.get_cmd_dict()) > 0:
            return

        msg = 'Commands not implemented'
        self.__logger.error(msg)
        raise NotImplementedError(msg)


    def get_cmd_dict(self, prefix: str = '', require_help: bool = True) -> dict:
        """
        Retrieves a dictionary of commands.

        Parameters
        ----------
        prefix : str, optional
            Prefix to add to the command name. Defaults to ''.
        require_help : bool, optional
            If True, commands that don't have a help entry will be skipped. Defaults to True.

        Returns
        -------
        dict
            A dictionary of commands, where the key is the command name and the value is a dictionary containing help and exec information.

            fmt:
            {
                [cmd_name:str] : {
                    'perm' : int,
                    'help' : str,
                    'exec' : Callable
                }
            }
        """
        cmd_dict = {
            attr.replace('cmd_', prefix) : getattr(self, attr)
            for attr in dir(self)
                if attr.startswith('cmd_') and hasattr(self, attr)
        }

        if not require_help:
            return cmd_dict

        # Remove commands that have invalid entries
        for cmd_name in list(cmd_dict):
            if not type(cmd_dict[cmd_name]) == dict:
                self.__logger.warning(f'\tCommand "{cmd_name}" does not have a help entry; Skipping...')
                del cmd_dict[cmd_name]
                continue

            if not cmd_dict[cmd_name]['help']:
                self.__logger.warning(f'\tCommand "{cmd_name}" does not have a valid help entry (missing "help"); Skipping...')
                del cmd_dict[cmd_name]
                continue

            if not cmd_dict[cmd_name]['exec']:
                self.__logger.warning(f'\tCommand "{cmd_name}" does not have a valid help entry (missing "exec"); Skipping...')
                del cmd_dict[cmd_name]
                continue

        return cmd_dict


    @staticmethod
    def arg(var_types: list[type] | type, is_optional: bool, info: str) -> str:
        if not isinstance(var_types, list):
            var_types = [ var_types ]

        opt_txt = '(optional)' if is_optional else ''
        var_txt = ','.join( str(var_type) for var_type in var_types )

        return f'{var_txt} {opt_txt} |  {info}'


    @staticmethod
    def ok(msg: Optional[str] = None) -> dict:
        """
        For bot API to return a success message

        Parameters
        ----------
        msg : str, optional
            Message to return. Defaults to None.

        Returns
        -------
        dict
            API response

            fmt: { 'status' : 0, 'msg' : str }
        """
        if msg == None: return { 'status' : 0 }
        else:           return { 'status' : 0, 'msg' : f'```{msg}```' }


    @staticmethod
    def err(msg: Optional[str] = None) -> dict:
        """
        For bot API to return an error message

        Parameters
        ----------
        msg : str, optional
            Message to return. Defaults to None.

        Returns
        -------
        dict
            API response

            fmt: { 'status' : -1, 'msg' : str }
        """
        if msg == None: return { 'status' : -1 }
        else:           return { 'status' : -1, 'msg' : f'```ansi\n\x1b[31;20m{msg}\x1b[0m```' }


    def cmd_about(self) -> Callable:
        """
        Retrieves the about text for the bot

        To be reimplemented in subclasses

        Returns
        -------
        Callable
            Function to execute when command is called
        """
        msg = 'Command \'about\' not implemented'
        self.__logger.error(msg)
        raise NotImplementedError(msg)


    def get_bot_moderators(self) -> list[int]:
        """
        Retrieves a list of user ids that are moderators for this bot.

        To be reimplemented in subclasses

        Returns
        -------
        list[int]
            List of user ids
        """
        msg = '\'get_bot_moderators\' not implemented'
        self.__logger.error(msg)
        raise NotImplementedError(msg)


    def validate_special_perm(self, requestor_id: int, args: tuple):
        """
        Validates if the requestor has special permissions to execute a command.

        To be reimplemented in subclasses

        Parameters
        ----------
        requestor_id : int
            User id of the user who called the command
        args : tuple
            Arguments passed to the command

        Raises
        ------
        NotImplementedError
            If not implemented in subclass
        """
        msg = '\'validate_special\' not implemented'
        self.__logger.error(msg)
        raise NotImplementedError(msg)


    def validate_request(self, cmd_key: tuple[int, int], args: tuple = ()):
        """
        Validates if the requestor has sufficient permissions to execute a command.

        Parameters
        ----------
        cmd_key : tuple[int, int]
            A tuple containing the user id of the user who called the command and the permission level of the command
        args : tuple
            Arguments passed to the command

        Returns
        -------
        bool
            Whether the requestor has enough permissions or not
        """
        perm, requestor_id = cmd_key

        # Check against bot owner
        if requestor_id == BotConfig['Core']['discord_admin_user_id']:
            warnings.warn(f'Validated bot owner for uid {requestor_id}')
            return True

        if perm > Cmd.PERMISSION_MOD:
            # The command is an admin command, disallow
            return False

        # Check against moderator
        bot_moderator_ids = self.get_bot_moderators()
        if requestor_id in bot_moderator_ids:
            warnings.warn(f'Validated bot moderator for uid {requestor_id}')
            return True

        if perm > Cmd.PERMISSION_SPECIAL:
            return False

        # Check against special role
        if self.validate_special_perm(requestor_id, args):
            warnings.warn(f'Validated special permission for uid {requestor_id}')
            return True

        if perm > Cmd.PERMISSION_PUBLIC:
            return False

        return True


    class help():

        def __init__(self, perm: int = 0, info: str | None = None, args: dict | None = None):
            self.info = info if info else ''
            self.args = args if args else {}
            self.help = { 'info' : self.info, 'args' : self.args }
            self.perm = perm


        def __call__(self, func: Callable, *args: list, **kwargs: dict) -> dict:
            return { 'perm' : self.perm, 'help' : self.gen_cmd_help, 'exec' : func }


        def gen_cmd_help(self) -> dict:
            args = zip(self.help['args'].keys(), self.help['args'].values())
            args = [ ' : '.join(arg) for arg in args ]

            msg = self.info
            if len(args) > 0: msg += '\n\nargs:\n  ' + '\n  '.join(args)
            else:             msg += '\n\nargs: None'

            return { 'status' : 0, 'msg' : f'```{msg}```' }
