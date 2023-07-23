from typing import Union

from core import BotBase
from core import Cmd
from core import Post, Topic


# This to be used as a template for other bots with basic explanatons what the important parts do
class TestBot(BotBase):

    # The enable flag which controls whether the bot will be active or not
    # Every other parameter is to be copy-pasted
    def __init__(self, core):
        BotBase.__init__(self, core, self.BotCmd, self.__class__.__name__, enable=False)


    # Things that need to be intialized or run after initialization. This is primarily
    # for inter-bot dependency cases, where one bot depends on another to function
    def post_init(self):
        pass


    # In here goes all the code for reading comment json
    def process_data(self, forum_data: Union[Post, Topic]):
        self.logger.debug('Bot process_data')
        return {}


    # The BotCmd is not required, but it enables the admin to be able to interface with the bot during runtime
    # It is to be extended from Cmd, which provides base functionality for constructing commands, and it is also
    # crucial it be nested in the Bot's class
    #
    # The command processor is what drives the bot's command interface, and accepts json formated requests like so:
    # {
    #   'bot'  : 'BotName',
    #   'cmd'  : 'CommandName',
    #   'args' : [ 'various', 'command args', 123, 'go here' ],
    #   'key'  : user_id
    # }
    #
    # This returns a reply:
    # {
    #   'status' : 0
    #   'msg'    : 'If the status is 0, then the command has succeeded. Otherwise it would be -1, which means it has failed'
    # }
    #
    # The msg field is option; it may or may not come in the reply. It is meant to either serve as info on why command has
    # failed or as a return value for a request
    class BotCmd(Cmd):

        # obj is what the commands interface with
        def __init__(self, logger, obj):
            self.logger = logger
            self.obj    = obj


        # This is one of the four function that are required to be defined in the derived class and serves to provide
        # a list of users who are allowed to use commands up to Cmd.PERMISSION_MOD level
        def get_bot_moderators(self):
            return []


        # This is one of the four function that are required to be defined in the derived class and serves to check
        # whether the user who requested the command (requestor_id) can use the command based on whatever conditions
        # specified in args. This might be the user id they are trying to access, their requestor id's specific
        # status, and so on.
        def validate_special_perm(self, requestor_id: int, args: tuple):
            return False


        # Cmd.help allows the command to have help info associated with it
        # Unless specified explitly when loading commands, commands that don't have help info associated will not load
        # cmd_about is one of the four function that are required to be defined in the derived class and serves to provide
        # a description of what the bot does.
        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Prints the about text for TestBot',
        args = {
        })
        def cmd_about(self, cmd_key: "tuple[int, int]"):
            # This uses a function defined in the Cmd super class to validate the request. Validation is
            # based on user permission. Note the cmd_key, which is required for any non public permission level.
            # The value for cmd_key is automatically passed on from the Command Processor, so you only need to worry
            # about including it when required.
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            # Notice the Cmd.ok and Cmd.err. These indicate a response from the command - either it
            # executed ok, or there was an errror. The message is optional.
            return Cmd.ok('This bot is as minimal as a fully featured bot can get. This to be used as a template for other bots')


        # cmd_help is one of the four function that are required to be defined in the derived class and server to provide
        # information on how the bot can be interfaced with
        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Prints the help text for TestBot',
        args = {
        })
        def cmd_help(self, cmd_key: "tuple[int, int]"):
            # Validate the request. Note there are the following permission levels:
            #   Cmd.PERMISSION_PUBLIC  - Anyone and their grandmother is allowed to use the command
            #   Cmd.PERMISSION_SPECIAL - Anyone can use the command, but there are certain restrictions on a case-by-case basis, which are evaluated by validate_special_perm
            #   Cmd.PERMISSION_MOD     - Only users that are returned in the get_bot_moderators function are allowed to use the command
            #   Cmd.PERMISSION_ADMIN   - Only the bot owner (you) can use the command
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            return Cmd.ok('A test bot. That\'s all...')
