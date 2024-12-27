import os, sys
import inspect
import warnings

from .DiscordClient import DiscordClient


# \TODO: This doesn't allow to casscade exceptions
# \TODO: Redo this as a general bot exception to be used for exceptions that we don't want a stacktrace for
class BotException(Exception):

    def __init__(self, msg: str, show_traceback: bool = True):
        Exception.__init__(self, msg)

        trace_text = ''
        exc_info = sys.exc_info()

        if exc_info[0] is not None:
            trace = exc_info[2]

            while True:
                frame = trace.tb_frame
                trace_text += f'{frame.f_code.co_filename}:{frame.f_lineno} in {frame.f_code.co_name}\n'

                trace_tmp = trace.tb_next
                if not trace_tmp:
                    lines, lineno = inspect.getsourcelines(trace.tb_frame.f_code)

                    line_start = max(0,          trace.tb_frame.f_lineno - lineno - 3)
                    line_end   = min(len(lines), trace.tb_frame.f_lineno - lineno + 3)

                    trace_text += f''.join(lines[line_start : line_end])
                    break

                trace = trace_tmp

            trace_text = f'```py\n{trace_text}```'

        msg = f'**{msg}**\n\n' + trace_text
        msg = msg.replace(f'{os.getcwd()}{os.sep}', '')

        warnings.warn(msg, RuntimeWarning)
