import shutil
import time
import logging
import pytest

from bs4 import BeautifulSoup

from core.BotConfig import BotConfig
from core.BotCore import BotCore
from core.parser import Topic, Post



class BotCoreTest(BotCore):

    def check_db(self):
        """
        Implement required `check_db` as stub
        """
        pass


class TestBotCore:

    __logger = logging.getLogger(__qualname__)

    @classmethod
    def setup_class(cls):
        cls.__logger.setLevel(logging.DEBUG)

        # Override botconfig settings
        BotConfig['Core'].update({
            'is_dbg'          : True,
            'bots_path'       : 'src/bots',
            'db_path_dbg'     : 'db/test',
            'api_port'        : 0,
        })


    def setup_method(self, method):
        self.__del_db()

        self.__logger.info('Creating new BotCore...')
        self.core = BotCoreTest()


    def teardown_method(self, method):
        """
        Reset the database after each test to start each test clean
        """
        self.__del_db()


    def __del_db(self):
        self.__logger.info('Deleting db...')
        time_start = time.time()

        while True:
            try: shutil.rmtree(BotConfig['Core']['db_path_dbg'])
            except PermissionError as e:
                time.sleep(0.1)

                if time.time() - time_start > 1:
                    pytest.fail(f'Failed to delete db - something is using it: {e}')
                    break

            except FileNotFoundError:
                break


    @staticmethod
    def __get_post() -> Post:
        with open('src/tests/unit_tests/forum_test_page.htm', 'rb') as test_forum_page:
            content = test_forum_page.read()

        root  = BeautifulSoup(content, "lxml")
        topic = Topic(root)

        return topic.first_post


    def test_bots(self):
        # Just make sure it does not crash
        bot = self.core.get_bot('TestBot')
        assert bot.name == 'TestBot'


    def test_forum_driver(self):
        # Just make sure it does not crash
        self.core.forum_driver(TestBotCore.__get_post())
