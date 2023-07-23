from typing import Optional, Callable, Union
import logging

from core import BotBase

class Cmd():

    PERMISSION_PUBLIC  = 0  # Anyone can use this command
    PERMISSION_SPECIAL = 1  # Special roles can use this command + mod + admin
    PERMISSION_MOD     = 2  # Mods roles can use this command + admin
    PERMISSION_ADMIN   = 3  # Only admin is able to use this command

    def __init__(self, logger: logging.Logger, obj: BotBase):
        self.logger = logger
        self.obj    = obj

        msg = 'Commands not implemented'
        logger.error(msg)
        raise NotImplementedError(msg)


    def get_cmd_dict(self, prefix: str = '', require_help: bool = True) -> dict:
        cmd_dict = {
            attr.replace('cmd_', prefix) : getattr(self, attr)
            for attr in dir(self)
                if attr.startswith('cmd_') and hasattr(self, attr)
        }

        if not require_help:
            return cmd_dict

        for cmd_name in list(cmd_dict):
            if not type(cmd_dict[cmd_name]) == dict:
                self.logger.warning(f'\tCommand "{cmd_name}" does not have a help entry; Skipping...')
                del cmd_dict[cmd_name]
                continue

            if not cmd_dict[cmd_name]['help']:
                self.logger.warning(f'\tCommand "{cmd_name}" does not have a valid help entry (missing "help"); Skipping...')
                del cmd_dict[cmd_name]
                continue

            if not cmd_dict[cmd_name]['exec']:
                self.logger.warning(f'\tCommand "{cmd_name}" does not have a valid help entry (missing "exec"); Skipping...')
                del cmd_dict[cmd_name]
                continue

        return cmd_dict


    @staticmethod
    def arg(var_types: "Union[list[str], str]", is_optional: bool, info: str) -> str:
        if type(var_types) is not list:
            var_types = [ var_types ]

        opt_text  = '(optional)' if is_optional else ''
        var_types = ','.join([ str(var_type) for var_type in var_types ])

        return f'{var_types} {opt_text} |  {info}'


    @staticmethod
    def ok(msg: Optional[str] = None) -> dict:
        if msg == None: return { 'status' : 0 }
        else:           return { 'status' : 0, 'msg' : msg }


    @staticmethod
    def err(msg: Optional[str] = None) -> dict:
        if msg == None: return { 'status' : -1 }
        else:           return { 'status' : -1, 'msg' : msg }


    def cmd_about(self):
        msg = 'Command \'about\' not implemented'
        self.logger.error(msg)
        raise NotImplementedError(msg)


    def get_bot_moderators(self):
        msg = '\'get_bot_moderators\' not implemented'
        self.logger.error(msg)
        raise NotImplementedError(msg)


    def validate_special_perm(self, requestor_id: int, args: tuple):
        msg = '\'validate_special\' not implemented'
        self.logger.error(msg)
        raise NotImplementedError(msg)


    def validate_request(self, cmd_key: "tuple[int, int]", args: tuple = ()):
        perm, requestor_id = cmd_key

        # Check against bot owner
        if requestor_id == self.obj.get_cfg('Core', 'discord_admin_user_id'): return True
        if perm > Cmd.PERMISSION_MOD: return False

        # Check against moderator
        bot_moderator_ids = self.get_bot_moderators()
        if requestor_id in bot_moderator_ids: return True
        if perm > Cmd.PERMISSION_SPECIAL: return False

        # Check against special role
        if self.validate_special_perm(requestor_id, args): return True
        if perm > Cmd.PERMISSION_PUBLIC: return False

        return True


    class help():

        def __init__(self, perm: int = 0, info: str = None, args: dict = None):
            self.info = info
            self.args = args
            self.help = { 'info' : self.info, 'args' : self.args }
            self.perm = perm


        def __call__(self, func: Callable, *args: list, **kwargs: dict):
            return { 'perm' : self.perm, 'help' : self.gen_cmd_help, 'exec' : func }


        def gen_cmd_help(self):
            args = zip(self.help['args'].keys(), self.help['args'].values())
            args = [ ' : '.join(arg) for arg in args ]

            msg = self.info
            if len(args) > 0: msg += '\n\nargs:\n' + '\n\t'.join(args)
            else:             msg += '\n\nargs: None'

            return { 'status' : 0, 'msg' : msg }
