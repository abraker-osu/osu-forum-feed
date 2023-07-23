import traceback
import logging


# \TODO: This doesn't allow to casscade exceptions
# \TODO: Redo this as a general bot exception to be used for exceptions that we don't want a stacktrace for
class BotException(Exception):
    def __init__(self, logger: logging.Logger, msg: str, show_traceback=True):
        Exception.__init__(self, msg)
