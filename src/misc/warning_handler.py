import os
import logging
import warnings

from core.DiscordClient import DiscordClient



def warning_formatter(msg: warnings.WarningMessage):
    category = msg.category.__name__
    s = f'{msg.filename}:{msg.lineno}: {category}: {msg.message}\n'

    if msg.line is None:
        try:
            import linecache
            line = linecache.getline(msg.filename, msg.lineno)
        except Exception:
            # When a warning is logged during Python shutdown, linecache
            # and the import machinery don't work anymore
            line = None
            linecache = None
    else:
        line = msg.line

    if line:
        s += f'  {line.strip()}\n'

    if msg.source is not None:
        # Logging a warning should not raise a new exception:
        # catch Exception, not only ImportError and RecursionError.
        try: import tracemalloc
        except Exception:
            # don't suggest to enable tracemalloc if it's not available
            tracing = True
            tb = None
        else:
            tracing = tracemalloc.is_tracing()

            try: tb = tracemalloc.get_object_traceback(msg.source)
            except Exception:
                # When a warning is logged during Python shutdown, tracemalloc
                # and the import machinery don't work anymore
                tb = None

        if tb is not None:
            s += 'Object allocated at (most recent call last):\n'
            for frame in tb:
                s += f'  File "{frame.filename}", lineno {frame.lineno}\n'

                try:
                    if linecache is not None:
                        line = linecache.getline(frame.filename, frame.lineno)
                    else:
                        line = None
                except Exception:
                    line = None
                if line:
                    line = line.strip()
                    s += '    %s\n' % line
        elif not tracing:
            s += f'{category}: Enable tracemalloc to get the object allocation traceback\n'

    return s


def warning_handler(message: Warning | str, category: type[Warning], filename: str, lineno: int, file: None = None, line: None | str = None):
    if isinstance(message, Warning):
        message = str(message)

    filename = os.path.basename(filename) if filename else ''
    msg = warnings.WarningMessage(message, category, filename, lineno, line = line, source = file)

    if category is DeprecationWarning:
        module = msg.filename.split('.')[0]
        logging.getLogger(module).info(f'{msg.filename}:{msg.lineno}: {msg.message}')
        return

    if category is RuntimeWarning:
        msg = warning_formatter(msg)
    else:
        msg = f'{file}: {message}'

    assert isinstance(msg, str), f'Unexpected message type: {type(msg)}'

    DiscordClient.request('admin/post', {
        'src'      : 'core' if not file else str(file),
        'contents' : str(msg)
    })


warnings.showwarning = warning_handler
warnings.simplefilter('always')
warnings.filterwarnings('ignore', category=DeprecationWarning, append=True)
warnings.warn('`Installed warning handler`', UserWarning, source='core')
