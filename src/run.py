import sys

if sys.version_info < (3, 8):
    print('Python 3.8 or later is required!')
    sys.exit(1)

import logging
import traceback
import os
import pathlib

import yaml

from core.Logger import LoggerClass
from core import ForumMonitor


excepthook_old = sys.excepthook
def exception_hook(exctype, value, tb):
    trace = ''.join(traceback.format_exception(exctype, value, tb))
    logging.getLogger('BotCore').exception(trace)
    sys.exit(1)
sys.excepthook = exception_hook




if __name__ == '__main__':
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    root = os.path.abspath(os.getcwd())
    log_path      = config['Core']['log_path']      = pathlib.Path(f'{root}/{config["Core"]["log_path"]}')
    bots_log_path = config['Core']['bots_log_path'] = pathlib.Path(f'{root}/{config["Core"]["bots_log_path"]}')
    bots_path     = config['Core']['bots_path']     = pathlib.Path(f'{root}/{config["Core"]["bots_path"]}')

    if not os.path.exists(log_path):
        os.makedirs(log_path)

    if not os.path.exists(bots_log_path):
        os.makedirs(bots_log_path)

    if not os.path.exists(bots_path):
        print('Fatal Error: Bot directory not found!')
        exit(404)

    logging.setLoggerClass(LoggerClass(log_path, config['Core']['is_dbg']))

    # \TODO: Consider this: http://www.bbarrows.com/blog/2012/09/24/implementing-exception-logging-in-python/

    forum_monitor = ForumMonitor(config)
    forum_monitor.run()
