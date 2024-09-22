import traceback
import os

from .DiscordClient import DiscordClient


# \TODO: This doesn't allow to casscade exceptions
# \TODO: Redo this as a general bot exception to be used for exceptions that we don't want a stacktrace for
class BotException(Exception):

    def __init__(self, msg: str, show_traceback: bool = True):
        Exception.__init__(self, msg)

        cwd = f'{os.getcwd()}{os.sep}'
        msg = f"`{msg.replace(cwd, '')}`"

        trace = traceback.format_exc()
        if trace != 'NoneType: None\n':
            trace = f"```py\n{traceback.format_exc().replace(cwd, '')}\n```"
        else:
            trace = ''

        DiscordClient.request('admin/post', {
            'src' : 'forumbot',
            'contents' : f'**{msg}**\n\n' + trace if show_traceback else msg
        })
