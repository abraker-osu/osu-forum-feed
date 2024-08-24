import os
import time
import logging
import random

import pytest
from bs4 import BeautifulSoup

from core.BotCore import BotCore
from core.parser import Topic, Post



class BotCoreTest(BotCore):

    def check_db(self):
        """
        Implement required `check_db` as stub
        """
        pass


class TestBotCore:

    @classmethod
    def setup_class(cls):
        cls.logger = logging.getLogger('TestBotCore')
        cls.logger.setLevel(logging.DEBUG)


    def setup_method(self, method):
        self.logger.info('Creating new BotCore...')
        self.core = BotCoreTest({
            'Core' : {
                'is_dbg'    : True,
                'db_path'   : 'db-test.json',
                'bots_path' : 'src/bots'
            },
            'ThreadNecroBot' : {
                'post_id'      :  random.randint(1, 10000),
                'topic_id'     :  random.randint(1, 10000),

                'post_id_dbg'  :  random.randint(1, 10000),
                'topic_id_dbg' :  random.randint(1, 10000),
            },
            'ForumFeedBot' : {
                'discord_bot_port' : random.randint(1, 10000),
            }
        })


    def teardown_method(self, method):
        """
        Reset the database after each test to start each test clean
        """
        self.logger.info('Deleting db...')
        self.core.__del__()
        time_start = time.time()

        while True:
            try: os.remove('db-test.json')
            except PermissionError:
                time.sleep(0.1)
            except FileNotFoundError:
                break
            else:
                break

            if time.time() - time_start > 1:
                self.logger.info(f'Failed to delete db - something is using it.')
                break


    @staticmethod
    def __get_post() -> Post:
        logger = logging.Logger(TestBotCore.__name__)
        with open('src/tests/unit_tests/forum_test_page.htm', 'rb') as test_forum_page:
            content = test_forum_page.read()

        root  = BeautifulSoup(content, "lxml")
        topic = Topic(root, logger)

        return topic.first_post


    def test_db(self):
        # Just make sure it does not crash
        test_table = self.core.get_db_table('test')


    def test_bots(self):
        # Just make sure it does not crash
        bot = self.core.get_bot('TestBot')
        assert bot.get_name() == 'TestBot'


    def test_forum_driver(self):
        # Just make sure it does not crash
        self.core.forum_driver(TestBotCore.__get_post())
