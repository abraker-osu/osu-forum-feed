import sys

import logging
if sys.version_info < (3, 10):
    logging.critical('Python 3.10 or later is required!')
    sys.exit(1)

import traceback
import os
import pathlib

from core.ForumMonitor import ForumMonitor
from core.BotConfig import BotConfig


excepthook_old = sys.excepthook
def exception_hook(exctype, value, tb):
    trace = ''.join(traceback.format_exception(exctype, value, tb))
    logging.getLogger('BotCore').exception(trace)
    sys.exit(1)
sys.excepthook = exception_hook




if __name__ == '__main__':
    root = os.path.abspath(os.getcwd())
    log_path      = BotConfig['Core']['log_path']      = pathlib.Path(f'{root}/{BotConfig["Core"]["log_path"]}')
    bots_log_path = BotConfig['Core']['bots_log_path'] = pathlib.Path(f'{root}/{BotConfig["Core"]["bots_log_path"]}')
    bots_path     = BotConfig['Core']['bots_path']     = pathlib.Path(f'{root}/{BotConfig["Core"]["bots_path"]}')

    if not os.path.exists(log_path):
        os.makedirs(log_path)

    if not os.path.exists(bots_log_path):
        os.makedirs(bots_log_path)

    if not os.path.exists(bots_path):
        logging.critical('Fatal Error: Bot directory not found!')
        exit(404)

    # \TODO: Consider this: http://www.bbarrows.com/blog/2012/09/24/implementing-exception-logging-in-python/
    ForumMonitor.run()
