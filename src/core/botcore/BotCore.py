import os
import importlib
import logging

import config
from core.botcore.BotException import BotException

from .BotBase import BotBase


class BotCore():

    _version = 20210328

    def __init__(self):
        self.__logger = logging.getLogger(__class__.__name__)
        self.__logger.info(f'Forum Bot version {BotCore._version}')
        self.__logger.info('BotCore initializing...')

        self.__bots: dict[str, BotBase] = {}

        try: self.__init_bots()
        except Exception as e:
            self.__logger.critical(str(e))
            raise e


    def __init_bots(self):
        self.__logger.info('Loading Bots...')

        bot_dir_files = os.listdir(config.bots_path)
        self.__logger.debug(f'Files found: {bot_dir_files}')

        bots = [ f[:-3] for f in bot_dir_files if f != '__init__.py' and f[-3:] == '.py' ]
        self.__logger.debug(f'Bots found: {bots}')

        for bot in bots:
            self.__logger.info(f'Importing bots.{bot}')
            module = importlib.import_module(f'bots.{bot}')

            try:
                self.__bots[bot] = getattr(module, bot)(self)
            except Exception as e:
                msg = (
                    f'Cannot load module for bot: {module}\n'
                    f'{e}'
                )
                raise BotException(self.__logger, msg)

        self.__logger.info('Running bot post initialization routines.')

        for name, bot in self.__bots.items():
            try: bot.post_init()
            except Exception as e:
                msg = (
                    f'Cannot run post initialization for {name} bot; Function bot.post_init() failed!\n'
                    f'{e}'
                )
                raise BotException(self.__logger, msg)


    def forum_driver(self, forum_data):
        for bot in self.__bots.values():
            bot.event(forum_data)


    def get_bot(self, bot_name):
        return self.__bots[bot_name]
