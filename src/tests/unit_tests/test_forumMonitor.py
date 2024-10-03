from typing import Optional
import shutil

import logging
import time
import requests
import pytest

from threading import Thread, Lock
from requests.models import Response

from bs4 import BeautifulSoup


from core.parser import Topic, Post
from core.BotConfig import BotConfig

# Override botconfig settings
BotConfig['Core'].update({
    'is_dbg'          : True,
    'bots_path'       : 'src/bots',
    'db_path_dbg'     : 'db/test',
    'api_port'        : 0,

    'latest_post_id'  : 0,
    'rate_post_max'   : 0.1,
    'rate_post_warn'  : 0.1,
    'rate_post_min'   : 0.1,
    'rate_fetch_fail' : 0.1,
})

# These must be imported after the BotConfig override
#  so that they can capture the changed settings
from core.ForumMonitor import ForumMonitor
from core.SessionMgrV2 import SessionMgrV2



class TestForumMonitor:
    """
    NOTE: The forum monitor testing makes use of "src/tests/unit_tests/forum_test_page.htm" for requested data
    instead of actually fetching the data from the live site. This speeds up the testing, but also
    allows the possibility of the forum test page not being up to date with the actual site.
    """

    __last_id_check = None
    __id_check_lock = Lock()

    __logger = logging.getLogger(__qualname__)

    @classmethod
    def setup_class(cls):
        cls.__logger.setLevel(logging.DEBUG)

        cls.__old_get_post = SessionMgrV2.get_post
        SessionMgrV2.get_post = cls.__get_post


    @classmethod
    def teardown_class(cls):
        SessionMgrV2.get_post = cls.__old_get_post


    def setup_method(self, method):
        """
        Reset ForumMonitor parameters after each test to start each test clean
        """
        self.__del_db()

        # This re-initializes the forum monitor by executing its __init__
        # This works because the ForumMonitor class is made a singleton in
        #   the ForumMonitor module by overriding the class type attrib name
        #    with an instance of the class.
        self.__logger.info('Creating new forum monitor...')
        type(ForumMonitor)()
        ForumMonitor.forum_driver = lambda _: ...

        ForumMonitor._ForumMonitor__post_rate       = 0.1
        ForumMonitor._ForumMonitor__rate_fetch_fail = 0.1
        ForumMonitor._ForumMonitor__latest_post_id  = None
        ForumMonitor._ForumMonitor__check_post_ids  = [ 0 ]


    def teardown_method(self, method):
        self.__del_db()


    def __del_db(self):
        # This is to close the db and other resources used by the forum monitor
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


    def check_post_ids(self):
        return ForumMonitor._ForumMonitor__check_post_ids


    def check_new_post(self):
        ForumMonitor._ForumMonitor__check_new_post()


    @staticmethod
    def __get_post(post_id: int | str, page: Optional[requests.Response] = None) -> Post:
        with open('src/tests/unit_tests/forum_test_page.htm', 'rb') as test_forum_page:
            content = test_forum_page.read()

        root = BeautifulSoup(content, "lxml")
        topic = Topic(root)

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

        with open('src/tests/unit_tests/forum_test_page.htm', 'rb') as test_forum_page:
            page._content = test_forum_page.read()

        return thread_url, page


    def test_initial_conditions(self):
        """
        On start,
        - The db path is expected to be set to the test path
        - The forum monitor has `latest_post_id` is initialized to the default config because it has not checked for any posts yet
        - Has 1 initial post id to bootstrap off and start the check on
        """
        assert ForumMonitor._db_path == BotConfig['Core']['db_path_dbg'], f'Unexpected db path | db_path = {ForumMonitor._db_path}'

        # If any of these fail, then every proceeding test is expected to fail as well
        assert ForumMonitor.get_latest_post() == BotConfig['Core']['latest_post_id'], f'Unexpected latest post id | lastest_post_id = {ForumMonitor.get_latest_post()}'

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

        ForumMonitor.fetch_post = TestForumMonitor.fetch_none
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

        ForumMonitor.fetch_post = TestForumMonitor.fetch_not_found
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

        ForumMonitor.fetch_post = TestForumMonitor.fetch_too_many_requests
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
        ForumMonitor.handle_new_post([ post_id ], 0, page)

        # Should be 1 since all prev ids are discard and new one is added
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'


    def test_post_ok(self):
        # Make sure initial condition
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        ForumMonitor.fetch_post = TestForumMonitor.fetch_ok
        self.check_new_post()

        # Should be 1 since it resets the post ids to check to latest one
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'


    def test_post_multiple_ok(self):
        """
        Sets up 3 posts to be ok
        """
        # Make sure initial condition
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        ForumMonitor.fetch_post = TestForumMonitor.fetch_ok

        for i in range(3):
            self.__logger.info(f'Checking new post ({i})...')
            self.check_new_post()

            # Should be 1 since all posts are ok
            assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'


    def test_post_404_ok_after_10(self):
        """
        Sets up 9 posts to be error 404 (not found) with the 10th one being ok
        """
        # Make sure initial condition
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        ForumMonitor.fetch_post = TestForumMonitor.fetch_not_found

        for i in range(9):
            self.check_new_post()

            # Should be going up as it searches for an ok post
            assert len(self.check_post_ids()) == i + 2, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        ForumMonitor.fetch_post = TestForumMonitor.fetch_ok
        self.check_new_post()

        # Should be 1 since it resets the post ids to check to latest one
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'


    def test_post_429_ok_after_10(self):
        """
        Sets up 9 posts to be error 429 (too many request) with the 10th one being ok
        """
        # Make sure initial condition
        assert len(self.check_post_ids()) == 1, f'Unexpected number of thread ids to be checked | check_post_ids = {self.check_post_ids()}'

        ForumMonitor.fetch_post = TestForumMonitor.fetch_too_many_requests

        for _ in range(9):
            self.check_new_post()

            # Should not be going up in response to too many requests
            assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        ForumMonitor.fetch_post = TestForumMonitor.fetch_ok
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
            ForumMonitor._ForumMonitor__post_rate = 0.1

            self.__logger.info(f'Will set post id {post_id} to ok')

            # The `handle_new_post` func will be fetching 404's until the Nth post
            ForumMonitor.fetch_post = TestForumMonitor.fetch_not_found

            # This needs to be multithreaded so the test is able to change post id status mid-way
            multi_threaded = Thread(target=ForumMonitor.handle_new_post, args=(check_post_ids, 19, page))
            multi_threaded.start()

            # Time the sleep to be about in sync with post checking and then change the post
            # fetch to be ok on the Nth post id. It should stop checking there
            while TestForumMonitor.__last_id_check + 1 < post_id:
                time.sleep(0.01)

            ForumMonitor.fetch_post = TestForumMonitor.fetch_ok

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
        ForumMonitor.fetch_post = TestForumMonitor.fetch_ok

        # Precondition that latest ok post id is #0
        self.check_post_ids()[0] = 0

        for i in range(3):
            self.__logger.info(f'Checking new post ({i})...')
            self.check_new_post()

            # Should be 1 since all posts are ok
            assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

            # Make sure post ids to check for are incrementing
            assert self.check_post_ids()[0] == i + 1, f'Unexpected post_id | check_post_ids = {self.check_post_ids()}'

        # Scramble the check post ids for good measure
        self.check_post_ids()[0] = 353

        self.__logger.info(f'Creating new forum monitor...')
        type(ForumMonitor)()

        # Restart forum monitor
        # Initial conditions and overides
        ForumMonitor._ForumMonitor__post_rate       = 0.1
        ForumMonitor._ForumMonitor__rate_fetch_fail = 0.1
        ForumMonitor._ForumMonitor__latest_post_id  = None

        # Should be 3 as post id #2 is latest one checked before forum monitor restarted
        assert ForumMonitor.get_latest_post() == 3

        # Should be 1 as initial condition
        assert len(self.check_post_ids()) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids()}'

        # Should be 3 as post id #2 is latest one checked before forum monitor restarted
        assert self.check_post_ids()[0] == 3, f'Unexpected post id to check for | check_post_ids = {self.check_post_ids()}'
