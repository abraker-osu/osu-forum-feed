import os
import importlib
import logging

from .BotException import BotException
from .BotBase import BotBase
from .parser import Post, Topic


class BotCore():

    class ConfigKeyError(Exception):
        ...


    def __init__(self, config: dict):
        self.__logger = logging.getLogger(__class__.__name__)
        self.__logger.info('BotCore initializing...')

        self.__config = config
        self.runtime_quit = False

        self.db_path = self.get_cfg('Core', 'db_path_dbg') if self.get_cfg('Core', 'is_dbg') else self.get_cfg('Core', 'db_path')
        os.makedirs(self.db_path, exist_ok=True)
        self.check_db()

        self.__bots: dict[str, BotBase] = {}

        try: self.__init_bots()
        except Exception as e:
            self.__logger.critical(str(e))
            raise e


    def __init_bots(self):
        self.__logger.info('Loading Bots...')

        bot_dir_files = os.listdir(self.get_cfg('Core', 'bots_path'))
        self.__logger.debug(f'Files found: {bot_dir_files}')

        bots = [ f[:-3] for f in bot_dir_files if f != '__init__.py' and f[-3:] == '.py' ]
        self.__logger.debug(f'Bots found: {bots}')

        for bot in bots:
            self.__logger.info(f'Importing bots.{bot}')
            module = importlib.import_module(f'bots.{bot}')

            try: self.__bots[bot] = getattr(module, bot)(self)
            except BotCore.ConfigKeyError as e:
                self.__logger.error(f'Cannot load "{bot}"; Missing config key: "{e}"')
                continue
            except Exception as e:
                msg = (
                    f'Cannot load module for bot: {module}\n'
                    f'{e}'
                )
                raise BotException(self.__logger, msg)

        self.__logger.info('Running bot post initialization routines.')

        for name, bot in self.__bots.items():
            try: bot.post_init()
            except BotCore.ConfigKeyError as e:
                self.__logger.error(f'Cannot run post initialization for "{name}"; Missing config key: "{e}"')
                continue
            except Exception as e:
                msg = (
                    f'Cannot run post initialization for "{name}"; Function bot.post_init() failed!\n'
                    f'{e}'
                )
                raise BotException(self.__logger, msg)


    def forum_driver(self, post: Post):
        for bot in self.__bots.values():
            bot.event(post)


    def get_bot(self, name: str):
        return self.__bots[name]


    def get_cfg(self, src: str, key: str):
        try: return self.__config[src][key]
        except KeyError as e:
            raise BotCore.ConfigKeyError(f'{src}.{key}') from e


    def check_db(self):
        raise NotImplementedError



