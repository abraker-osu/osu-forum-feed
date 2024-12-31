import os
import importlib
import logging
import datetime
import warnings

from .BotException import BotException
from .BotConfig import BotConfig
from .BotBase import BotBase
from .parser import Post

from api.ApiServer import ApiServer


class BotCore():

    class ConfigKeyError(Exception):
        ...


    def __init__(self):
        self.__logger = logging.getLogger(__class__.__name__)
        self.__logger.info('BotCore initializing...')

        self.__time_start = datetime.datetime.now()
        self.runtime_quit = False

        # Initialize the botcore database
        # Database path can be a debug path or a production path
        self._db_path = BotConfig['Core']['db_path_dbg'] if BotConfig['Core']['is_dbg'] else BotConfig['Core']['db_path']
        os.makedirs(self._db_path, mode=0o660, exist_ok=True)
        self.check_db()

        # Initialize the bot modules
        self.__bots: dict[str, BotBase] = {}

        try: self.__init_bots()
        except Exception as e:
            raise BotException(
                f'Failed to initialize bots\n'
                f'{e.__class__.__name__}: {e}'
            ) from e


    def __init_bots(self):
        self.__logger.info('Loading Bots...')

        # Look into the bots directory for any python files. Those are considered to be bot modules,
        # excluding the __init__.py file.
        bot_dir_files = os.listdir(BotConfig['Core']['bots_path'])
        self.__logger.debug(f'Files found: {bot_dir_files}')

        bots: list[str] = [ f[:-3] for f in bot_dir_files if f != '__init__.py' and f[-3:] == '.py' ]
        self.__logger.debug(f'Bots found: {bots}')

        # For each file found, import it and initialize an instance of the bot via `getattr`
        for bot in bots:
            self.__logger.info(f'Importing bots.{bot}')
            module = importlib.import_module(f'bots.{bot}')

            try: self.__bots[bot] = getattr(module, bot)()
            except BotCore.ConfigKeyError as e:
                BotException(f'Cannot load "{bot}"; Missing config key: "{e}"')
                continue
            except Exception as e:
                BotException((
                    f'Cannot load module for bot: {module}\n'
                    f'{e.__class__.__name__}: {e}'
                ))
                continue

        self.__logger.info('Running bot post initialization routines.')

        # Run bot post initialization routines
        for name, bot in self.__bots.items():
            try: bot.post_init()
            except BotCore.ConfigKeyError as e:
                BotException(f'Cannot run post initialization for "{name}"; Missing config key: "{e}"')
                continue
            except Exception as e:
                BotException(msg = (
                    f'Cannot run post initialization for "{name}"; Function bot.post_init() failed!\n'
                    f'{e.__class__.__name__}: {e}'
                ))
                continue

        # Now that all bots are initialized, initialize the API server
        ApiServer.init(list(self.__bots.values()))


    def forum_driver(self, post: Post):
        """
        For each bot, run the event function with the given post.

        Parameters
        ----------
        post: Post
            The post to process.
        """
        for bot in self.__bots.values():
            bot.event(post)


    def get_bot(self, name: str | None) -> BotBase | list[BotBase]:
        """
        Retrieve a bot instance by name.

        Parameters
        ----------
        name: str
            The name of the bot to retrieve.

        Raises
        ------
        KeyError
            If the bot does not exist.

        Returns
        -------
        BotBase
            The bot instance.
        """
        if isinstance(name, type(None)):
            return list(self.__bots.values())

        return self.__bots[name]


    def check_db(self):
        """
        Checks the integrity of the database.

        This method must be implemented by subclasses and should check
        the integrity of the database.

        Raises
        ------
        NotImplementedError
            If function is not implemented by subclasses.
        """
        raise NotImplementedError('This method must be implemented by subclasses.')


    def runtime(self) -> datetime.timedelta:
        return datetime.datetime.now() - self.__time_start
