import sys

if sys.version_info < (3, 8):
    print('Python 3.8 or later is required!')
    sys.exit(1)

import logging
import traceback
import os

import config
from core.botcore.Logger import Logger
from core import ForumMonitor


logging.setLoggerClass(Logger)


excepthook_old = sys.excepthook
def exception_hook(exctype, value, tb):
    trace = ''.join(traceback.format_exception(exctype, value, tb))
    logging.getLogger('BotCore').exception(trace)
    sys.exit(1)
sys.excepthook = exception_hook


if __name__ == '__main__':
    if 'config' not in sys.modules:
        print('Fatal Error: config not found!')
        exit(404)

    if not os.path.exists(config.log_path):
        os.makedirs(config.log_path)

    if not os.path.exists(config.bots_log_path):
        os.makedirs(config.bots_log_path)

    if not os.path.exists(config.bots_path):
        print('Fatal Error: Bot directory not found!')
        exit(404)

    # \TODO: Consider this: http://www.bbarrows.com/blog/2012/09/24/implementing-exception-logging-in-python/

    forum_monitor = ForumMonitor()
    forum_monitor.run()
