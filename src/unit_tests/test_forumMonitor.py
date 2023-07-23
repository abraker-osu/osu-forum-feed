from typing import Union, Optional
import os

import pytest
import logging
import time
import requests

from threading import Thread, Lock
from requests.models import Response

from bs4 import BeautifulSoup

from core.ForumMonitor import ForumMonitor
from core.parser import Topic, Post



class ForumMonitorTest(ForumMonitor):

    def _BotCore__init_bots(self):
        """
        Don't initialize bots for this testing
        """
        pass



class TestForumMonitor:
    """
    NOTE: The forum monitor testing makes use of "src/unit_tests/forum_test_page.htm" for requested data
    instead of actually fetching the data from the live site. This speeds up the testing, but also
    allows the possibility of the forum test page not being up to date with the actual site.
    """

    __last_id_check = None
    __id_check_lock = Lock()

    @classmethod
    def setup_class(cls):
        cls.logger = logging.getLogger('TestForumMonitor')
        cls.logger.setLevel(logging.DEBUG)


    def setup_method(self, method):
        """
        Reset ForumMonitor parameters after each test to start each test clean
        """
        self.logger.info('Creating new forum monitor...')
        self.forum_monitor = ForumMonitorTest(
            config  = {
                'Core' : {
                    'db_path'   : 'db-test.json',
                    'bots_path' : 'src/bots',

                    'latest_post_id': 9059432,

                    'rate_post_max'  :  0.1,
                    'rate_post_warn' :  0.1,
                    'rate_post_min'  :  0.1,
                    'rate_fetch_fail':  0.1,
                }
            },
            login = False
        )
        self.forum_monitor._ForumMonitor__logger          = self.logger

        self.forum_monitor._ForumMonitor__post_rate       = 0.1
        self.forum_monitor._ForumMonitor__rate_fetch_fail = 0.1
        self.forum_monitor._ForumMonitor__latest_post_id  = None
        self.forum_monitor._ForumMonitor__check_post_ids  = [ 0 ]

        self.forum_monitor.get_post                       = self.__get_post
        self.forum_monitor.forum_driver                   = lambda _: ...

        # Because BotCore.__del__ sets this to true
        self.runtime_quit = False


    def teardown_method(self, method):
        # This is to close the db and other resources used by the forum monitor
        self.forum_monitor.__del__()

        self.logger.info('Deleting db...')
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


    def latest_post_id(self):
        return self.forum_monitor._ForumMonitor__latest_post_id


    def check_post_ids(self):
        return self.forum_monitor._ForumMonitor__check_post_ids


    def check_new_post(self):
        self.forum_monitor._ForumMonitor__check_new_post()


    @staticmethod
    def __get_post(post_id: Union[int, str], page: Optional[requests.Response] = None) -> Post:
        logger = logging.Logger(TestForumMonitor.__name__)
        with open('src/unit_tests/forum_test_page.htm', 'rb') as test_forum_page:
            content = test_forum_page.read()

        root = BeautifulSoup(content, "lxml")
        topic = Topic(root, logger)

        return topic.first_post


    @staticmethod
    def fetch_none(thread_id):
        with TestForumMonitor.__id_check_lock:
            TestForumMonitor.__last_id_check = thread_id

        thread_url = ''
        page       = None

        return thread_url, page


    @staticmethod
    def fetch_not_found(thread_id):
        with TestForumMonitor.__id_check_lock:
            TestForumMonitor.__last_id_check = thread_id

        thread_url = ''

        page = Response()
        page.status_code = 404

        return thread_url, page


    @staticmethod
    def fetch_too_many_requests(thread_id):
        with TestForumMonitor.__id_check_lock:
            TestForumMonitor.__last_id_check = thread_id

        thread_url = ''

        page = Response()
        page.status_code = 429

        return thread_url, page


    def fetch_ok(thread_id):
        with TestForumMonitor.__id_check_lock:
            TestForumMonitor.__last_id_check = thread_id

        thread_url = ''

        page = Response()
        page.status_code = 200

        with open('src/unit_tests/forum_test_page.htm', 'rb') as test_forum_page:
            page._content = test_forum_page.read()

        return thread_url, page


    def test_initial_conditions(self):
        """
        On start,
        - The forum monitor has no `latest_post_id` loaded because it has not checked for any posts yet
        - Has 1 initial post id to bootstrap off and start the check on
        """
        # If any of these fail, then every proceeding test is expected to fail as well
        assert self.latest_post_id() is None, f'Unexpected latest post id | lastest_post_id = {self.latest_post_id()}'

        # Forum monitor starts by loading the latest saved thread and post ids to check for, so there should be
        # one in there to start with.
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'


    def test_post_non_page(self):
        """
        When failed to fetch the page,
        - Post id to check for remains the same as to retry getting it again. This happens if osu! site is down
        """
        # Make sure initial condition
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        self.forum_monitor.fetch_post = TestForumMonitor.fetch_none
        self.check_new_post()

        # Should remain unchanged since `check_new_post` simply quits when there is no fetched data
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'


    def test_post_not_found(self):
        """
        When page 404s,
        - It means page does not yet exists. The next id to check for is added to the list, but old one is also kept so it can be check for again
        """
        # Make sure initial condition
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        self.forum_monitor.fetch_post = TestForumMonitor.fetch_not_found
        self.check_new_post()

        # Should increase to 2 as it searches for a working post id
        assert len(self.check_post_ids()) == 2, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'


    def test_post_too_many_requests(self):
        """
        On too many requests,
        - The forum monitor should progressively slow down and retry getting the post again
        """
        # Make sure initial condition
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        # TODO: Validate check rate goes down

        self.forum_monitor.fetch_post = TestForumMonitor.fetch_too_many_requests
        self.check_new_post()

        # Should be 1 since too many requests is not indicative that current posts to check for are invalid
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'


    def test_handle_new_post_single(self):
        """
        On a successful post fetch,
        - The forum monitor discards all ids and inserts the next id into the list of post ids to check for
        """
        # Make sure initial condition
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        post_id = 9190565
        post_url, page = TestForumMonitor.fetch_ok(post_id)
        self.forum_monitor.handle_new_post([ post_id ], 0, page)

        # Should be 1 since all prev ids are discard and new one is added
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'


    def test_post_ok(self):
        # Make sure initial condition
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        self.forum_monitor.fetch_post = TestForumMonitor.fetch_ok
        self.check_new_post()

        # Should be 1 since it resets the post ids to check to latest one
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'


    def test_post_multiple_ok(self):
        """
        Sets up 3 posts to be ok
        """
        # Make sure initial condition
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        self.forum_monitor.fetch_post = TestForumMonitor.fetch_ok

        for i in range(3):
            self.logger.info(f'Checking new post ({i})...')
            self.check_new_post()

            # Should be 1 since all posts are ok
            assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'


    def test_post_404_ok_after_10(self):
        """
        Sets up 9 posts to be error 404 (not found) with the 10th one being ok
        """
        # Make sure initial condition
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        self.forum_monitor.fetch_post = TestForumMonitor.fetch_not_found

        for i in range(9):
            self.check_new_post()

            # Should be going up as it searches for an ok post
            assert len(self.check_post_ids()) == i + 2, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        self.forum_monitor.fetch_post = TestForumMonitor.fetch_ok
        self.check_new_post()

        # Should be 1 since it resets the post ids to check to latest one
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'


    def test_post_429_ok_after_10(self):
        """
        Sets up 9 posts to be error 429 (too many request) with the 10th one being ok
        """
        # Make sure initial condition
        assert len(self.check_post_ids()) == 1, f'Unexpected number of thread ids to be checked | check_post_ids = {self.check_post_ids()}'

        self.forum_monitor.fetch_post = TestForumMonitor.fetch_too_many_requests

        for _ in range(9):
            self.check_new_post()

            # Should not be going up in response to too many requests
            assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        self.forum_monitor.fetch_post = TestForumMonitor.fetch_ok
        self.check_new_post()

        # Should be 1 since it resets the post ids to check to latest one
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'


    def test_earlier_post_ok(self):
        """
        Sets up 20 posts. Iterates through first N posts to yield error 404 (not found) with the
        20th one being ok, but makes the N+1 one ok mid checking.

        It does not matter what the initial `check_post_ids` list in `ForumMonitor` is since the `handle_new_post`
        function gets passed a copy of it which is supplied here. However, the list does get modified by function,
        and what it gets modified to does matter.
        """
        # Make sure initial condition
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        check_post_ids = [ 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19 ]
        post_url, page = TestForumMonitor.fetch_ok(0)  # Get a page to pass to `handle_new_post`

        for post_id in check_post_ids[:-1]:
            TestForumMonitor.__last_id_check = -1

            # Make sure the post rate is consistent to 10 checks per second (handle_new_post will change this).
            self.forum_monitor._ForumMonitor__post_rate = 0.1

            self.logger.info(f'Will set post id {post_id} to ok')

            # The `handle_new_post` func will be fetching 404's until the Nth post
            self.forum_monitor.fetch_post = TestForumMonitor.fetch_not_found

            # This needs to be multithreaded so the test is able to change post id status mid-way
            multi_threaded = Thread(target=self.forum_monitor.handle_new_post, args=(check_post_ids, 19, page))
            multi_threaded.start()

            # Time the sleep to be about in sync with post checking and then change the post
            # fetch to be ok on the Nth post id. It should stop checking there
            while TestForumMonitor.__last_id_check + 1 < post_id:
                time.sleep(0.01)

            self.forum_monitor.fetch_post = TestForumMonitor.fetch_ok

            # Wait for the function to finish
            multi_threaded.join()

            # Make sure there is still one post id to check for
            assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

            # When it finds the post id ok, post id #x, it will put post id #x+1 into list of post ids to check for next
            assert self.check_post_ids()[0] == post_id + 1, f'Failed to find earlier post ID ok | check_post_ids = {self.check_post_ids()}'


    def test_post_id_check_recover(self):
        """
        Tests that the full scope of `check_new_post` is working correctly and that post ids to check for can be recovered.
        Goes through post checking process and finds ok posts until 3rd one, then ForumMonitor is restarted. The saved post_id
        is expected to be recovered from Db
        """
        # Make sure initial condition
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        # All of the posts will be ok
        self.forum_monitor.fetch_post = TestForumMonitor.fetch_ok

        # Precondition that latest ok post id is #0
        self.check_post_ids()[0] = 0

        for i in range(3):
            self.logger.info(f'Checking new post ({i})...')
            self.check_new_post()

            # Should be 1 since all posts are ok
            assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

            # Make sure post ids to check for are incrementing
            assert self.check_post_ids()[0] == i + 1, f'Unexpected post_id | check_post_ids = {self.check_post_ids()}'

        # Scramble the check post ids for good measure
        self.check_post_ids()[0] = 353

        self.logger.info(f'Creating new forum monitor...')

        # Restart forum monitor
        # Initial conditions and overides
        self.forum_monitor.__del__()
        self.forum_monitor = ForumMonitorTest(
            config  = {
                'Core' : {
                    'is_dbg'    : True,
                    'db_path'   : 'db-test.json',
                    'bots_path' : 'src/bots',

                    'latest_post_id': 9059432,

                    'rate_post_max'  :  0.1,
                    'rate_post_warn' :  0.1,
                    'rate_post_min'  :  0.1,
                    'rate_fetch_fail':  0.1,
                }
            },
            login = False
        )

        self.forum_monitor._ForumMonitor__post_rate       = 0.1
        self.forum_monitor._ForumMonitor__rate_fetch_fail = 0.1
        self.forum_monitor._ForumMonitor__logger          = self.logger
        self.forum_monitor._ForumMonitor__latest_post_id  = None

        self.forum_monitor.get_post                       = self.__get_post
        self.forum_monitor.forum_driver                   = lambda _: ...

        # Should be 3 as post id #2 is latest one checked before forum monitor restarted
        assert self.forum_monitor.get_latest_post() == 3

        # Should be 1 as initial condition
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        # Should be 3 as post id #2 is latest one checked before forum monitor restarted
        assert self.check_post_ids()[0] == 3, f'Unexpected post id to check for | check_post_ids = {self.check_post_ids()}'
