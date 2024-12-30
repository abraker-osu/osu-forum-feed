import shutil

import logging
import time
import requests
import pytest
import threading

from requests.models import Response

from bs4 import BeautifulSoup

from core.parser import Topic, Post
from core.BotConfig import BotConfig

from misc.threaded_obj import Threaded


# Override botconfig settings
BotConfig['Core'].update({
    'is_dbg'          : True,
    'bots_path'       : 'src/bots',
    'db_path_dbg'     : 'db/test',
    'api_port'        : 0,

    'latest_post_id'  : 0,
    'rate_post_max'   : 5.0,
    'rate_post_warn'  : 2.0,
    'rate_post_min'   : 0.1,
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
    __INITIAL_CHECK_RATE = 0.5*( BotConfig['Core']['rate_post_max'] + BotConfig['Core']['rate_post_min'] )

    __last_id_check = None
    __id_check_lock = threading.Lock()

    __logger = logging.getLogger(__qualname__)

    @classmethod
    def setup_class(cls):
        cls.__logger.setLevel(logging.DEBUG)

        cls.__old_get_post = SessionMgrV2.get_post
        SessionMgrV2.get_post = cls.__get_post
        ForumMonitor._BotCore__init_bots = lambda: None


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


    @property
    def check_post_ids(self) -> list[int]:
        return ForumMonitor._ForumMonitor__check_post_ids.get()


    @property
    def check_rate(self) -> float:
        return ForumMonitor._ForumMonitor__check_rate.get()


    @property
    def latest_post(self) -> int:
        return ForumMonitor.get_latest_post()


    def check_posts(self, check_post_ids: list[int], timeout: float) -> tuple[int, requests.Response | None]:
        return ForumMonitor._ForumMonitor__check_posts(check_post_ids, timeout)


    def check_posts_proc(self, timeout: float) -> tuple[int, requests.Response | None]:
        return ForumMonitor._ForumMonitor__check_posts_proc(recheck = False, timeout = timeout)



    @staticmethod
    def __get_post(post_id: int | str, page: requests.Response | None = None) -> Post:
        with open('src/tests/unit_tests/forum_test_page.htm', 'rb') as test_forum_page:
            content = test_forum_page.read()

        root = BeautifulSoup(content, "lxml")
        topic = Topic(root)

        return topic.first_post


    @staticmethod
    def fetch_none(post_id: int | str) -> requests.Response:
        raise TimeoutError()


    @staticmethod
    def fetch_not_found(post_id: int | str) -> requests.Response:
        with TestForumMonitor.__id_check_lock:
            TestForumMonitor.__last_id_check = int(post_id)

        page = Response()
        page.status_code = 404

        return page


    @staticmethod
    def fetch_too_many_requests(post_id: int | str) -> requests.Response:
        with TestForumMonitor.__id_check_lock:
            TestForumMonitor.__last_id_check = int(post_id)

        page = Response()
        page.status_code = 429

        return page


    @staticmethod
    def fetch_ok(post_id: int | str) -> requests.Response:
        with TestForumMonitor.__id_check_lock:
            TestForumMonitor.__last_id_check = int(post_id)

        page = Response()
        page.status_code = 200

        with open('src/tests/unit_tests/forum_test_page.htm', 'rb') as test_forum_page:
            page._content = test_forum_page.read()

        return page


    def test_initial_conditions(self):
        """
        On start,
        - The db path is expected to be set to the test path
        - The forum monitor has `latest_post_id` is initialized to the default config because it has not checked for any posts yet
        - Has 1 initial post id to bootstrap off and start the check on
        """
        assert ForumMonitor._db_path == BotConfig['Core']['db_path_dbg'], f'Unexpected db path | db_path = {ForumMonitor._db_path}'

        # If any of these fail, then every proceeding test is expected to fail as well
        assert self.latest_post == BotConfig['Core']['latest_post_id'], f'Unexpected latest post id | lastest_post_id = {self.latest_post}'

        # Forum monitor starts by loading the latest saved thread and post ids to check for, so there should be
        # one in there to start with.
        assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'

        # The first post id to check for should be the next id after the latest post
        assert self.latest_post + 1 == self.check_post_ids[0], f'Unexpected latest post id | lastest_post_id = {self.latest_post}'

        assert self.check_rate == self.__INITIAL_CHECK_RATE, f'Unexpected check rate | check_rate = {self.check_rate}'


    def test_post_non_page(self):
        """
        When failed to fetch the page,
        - Post id to check for remains the same as to retry getting it again. This happens if osu! site is down
        - It should also timeout since it's trying to get the same post id indefinitely
        """
        # Make sure initial condition
        assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'

        ForumMonitor.fetch_post = TestForumMonitor.fetch_none

        # It's not fetching valid posts, so it keeps on retrying the same post
        # This should timeout
        with pytest.raises(TimeoutError):
            post_id, page = self.check_posts([ 1, 2, 3 ], 0.1)

        # This should timeout as well
        with pytest.raises(TimeoutError):
            self.check_posts_proc(0.1)

        # Should remain unchanged since `check_new_post` simply quits when there is no fetched data
        assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'


    def test_post_not_found(self):
        """
        When page 404s,
        - It means page does not yet exists. The next id to check for is added to the list, but old one is also kept so it can be check for again
        """
        # Make sure initial condition
        assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'

        # When all pages 404, it should return (-1, None)
        ForumMonitor.fetch_post = TestForumMonitor.fetch_not_found
        post_id, page = self.check_posts([ 1, 2, 3 ], 60)

        assert post_id == -1, f'Unexpected post id returned | post_id = {post_id}'
        assert page is None, f'Unexpected page returned | page = {page}'

        post_id, page = self.check_posts_proc(60)

        assert post_id == -1, f'Unexpected post id returned | post_id = {post_id}'
        assert page is None, f'Unexpected page returned | page = {page}'

        # Should also append the next post id to check for as it searches for a working post id
        assert len(self.check_post_ids) == 2, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'


    def test_post_too_many_requests(self):
        """
        On too many requests,
        - The forum monitor should progressively slow down and retry getting the post again
        - It should also timeout since it's trying to get the same post id indefinitely
        """
        # Make sure initial condition
        assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'

        assert self.check_rate == self.__INITIAL_CHECK_RATE, f'Unexpected check rate | check_rate = {self.check_rate}'
        ForumMonitor.fetch_post = TestForumMonitor.fetch_too_many_requests

        N = 5
        with pytest.raises(TimeoutError):
            post_id, page = self.check_posts([ 0, 1, 2 ], N*self.__INITIAL_CHECK_RATE)

        # While not accurate arithmetic, waiting for `N*INITIAL_CHECK_RATE` ms should be close to the +0.1*N added check rate
        # In practice it's a little off since the loop time is 10 ms longer every iteration. For the purposes of checking that
        # it changes roughly as expected, this is good enough
        assert self.check_rate == pytest.approx(self.__INITIAL_CHECK_RATE + 0.1*N), f'Unexpected check rate | check_rate = {self.check_rate}'

        # Should be 1 since too many requests is not indicative that current posts to check for are invalid
        assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'


    def test_handle_new_post_single(self):
        """
        On a successful post fetch,
        - The forum monitor discards all ids and inserts the next id into the list of post ids to check for
        """
        # Make sure initial condition
        assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'

        ForumMonitor.fetch_post = TestForumMonitor.fetch_ok

        # Should return the first successful post
        post_id, page = self.check_posts([ 1, 2, 3 ], 0.1)
        assert post_id == 1, f'Unexpected post id returned | post_id = {post_id}'

        # Should return the first successful post
        post_id, page = self.check_posts_proc(0.1)
        assert post_id == 1, f'Unexpected post id returned | post_id = {post_id}'

        # Should be 1 since all prev ids are discard and new one is added
        assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'
        assert self.check_post_ids[0] == 2, f'Unexpected post ids to be checked | check_post_ids = {self.check_post_ids}'


    def test_post_multiple_ok(self):
        """
        Sets up 3 posts to be ok
        """
        # Make sure initial condition
        assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'

        ForumMonitor.fetch_post = TestForumMonitor.fetch_ok

        for i in range(3):
            self.__logger.info(f'Checking new post ({i})...')
            latest_post = self.latest_post
            post_id, page = self.check_posts_proc(0.1)

            # Should be 1 since all posts are ok
            assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'

            assert post_id == self.latest_post, f'Unexpected post id returned | post_id = {post_id}'
            assert self.latest_post == latest_post + 1, f'Unexpected latest post | latest_post = {self.latest_post}'
            assert self.check_post_ids[0] == self.latest_post + 1, f'Unexpected post ids to be checked | check_post_ids = {self.check_post_ids}'


    def test_post_404_ok_after_10(self):
        """
        Sets up 9 posts to be error 404 (not found) with the 10th one being ok
        """
        # Make sure initial condition
        assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'

        ForumMonitor.fetch_post = TestForumMonitor.fetch_not_found
        ForumMonitor._ForumMonitor__check_rate = Threaded(0.1)

        for i in range(9):
            self.__logger.info(f'Checking new post ({i})...')
            post_id, page = self.check_posts_proc(60)

            assert post_id == -1, f'Unexpected post id returned | post_id = {post_id}'
            assert page is None, f'Unexpected page returned | page = {page}'

            # Should be going up as it searches for an ok post
            assert len(self.check_post_ids) == i + 2, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'

        ForumMonitor.fetch_post = TestForumMonitor.fetch_ok
        post_id, page = self.check_posts_proc(0.1)

        # Should be 1 since it resets the post ids to check to latest one
        assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'


    def test_post_429_ok_after_10(self):
        """
        Sets up 9 posts to be error 429 (too many request) with the 10th one being ok
        """
        # Make sure initial condition
        assert len(self.check_post_ids) == 1, f'Unexpected number of thread ids to be checked | check_post_ids = {self.check_post_ids}'

        ForumMonitor.fetch_post = TestForumMonitor.fetch_too_many_requests

        for i in range(9):
            with pytest.raises(TimeoutError):
                post_id, page = self.check_posts_proc(0.1)

            # Should not be going up in response to too many requests
            assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'

            # TODO: Test check rate

        ForumMonitor.fetch_post = TestForumMonitor.fetch_ok
        post_id, page = self.check_posts_proc(0.1)

        # Should be 1 since it resets the post ids to check to latest one
        assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'

        # TODO Test check rate
        #  It should decrease after some time has passed after last too many requests
        #  Otherwise it should be same


    def test_earlier_post_ok(self):
        """
        Sets up 20 posts. Iterates through first N posts to yield error 404 (not found) with the
        Nth one being ok
        """
        # Do 10 posts because it desyncs with the oversimplified `check_rate` timing
        # estimation in the time.sleep as more posts are added
        for post_id in range(1, 10):
            # The `check_posts` func will be fetching 404's until the Nth post
            ForumMonitor.fetch_post = TestForumMonitor.fetch_not_found

            ForumMonitor._ForumMonitor__check_rate = Threaded(0.1)
            assert self.check_rate == 0.1, f'Unexpected post rate | check_rate = {self.check_rate}'

            ForumMonitor._ForumMonitor__latest_post_id = Threaded(0)
            assert self.latest_post == 0, f'Unexpected latest post | latest_post = {self.latest_post}'

            ForumMonitor._ForumMonitor__check_post_ids = Threaded([ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 ])

            # Should be going up as it searches for an ok post
            assert len(self.check_post_ids) == 10, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'

            self.__logger.info(f'Will set ok at post id {post_id}')

            # This needs to be multithreaded so the test is able to change post id status mid-way
            # Timeout is set to 60 seconds to avoid a TimeoutError being raised
            multi_threaded = threading.Thread(target=self.check_posts_proc, args=(60, ))
            multi_threaded.start()

            assert multi_threaded.is_alive() == True, f'Failed to start thread | thread = {multi_threaded}'

            # Time the sleep to be about in sync with post checking and then change the post
            # fetch to be ok on the Nth post id. It should exit checking after it sees the OK post
            time.sleep(1.1 * self.check_rate * (post_id - 1))

            # Wait for the function to finish
            ForumMonitor.fetch_post = TestForumMonitor.fetch_ok
            multi_threaded.join(timeout = 5)

            assert multi_threaded.is_alive() == False, f'Failed to stop thread | thread = {multi_threaded}'

            # According to the sleep timing, it should have stopped at the target post id
            assert self.latest_post == post_id, f'Unexpected latest post | latest_post = {self.latest_post}'

            # Make sure there is one post id to check for since a valid one was found
            assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'

            # When it finds the post id ok, post id #x, it will put post id #x+1 into list of post ids to check for next
            assert self.check_post_ids[0] == post_id + 1, f'Failed to find earlier post ID ok | check_post_ids = {self.check_post_ids}'


    def test_post_id_check_recover(self):
        """
        Tests that the full scope of `check_new_post` is working correctly and that post ids to check for can be recovered.
        Goes through post checking process and finds ok posts until 3rd one, then ForumMonitor is restarted. The saved post_id
        is expected to be recovered from Db
        """
        # All of the posts will be ok
        ForumMonitor.fetch_post = TestForumMonitor.fetch_ok

        # Precondition that latest ok post id is #0
        ForumMonitor.set_latest_post(-1)

        for i in range(3):
            self.__logger.info(f'Checking new post ({i})...')
            self.check_posts_proc(0.1)

            # Should be 1 since all posts are ok
            assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'

            # Make sure post ids to check for are incrementing
            assert self.check_post_ids[0] == i + 1, f'Unexpected post_id | check_post_ids = {self.check_post_ids}'

            assert self.latest_post == i, f'Unexpected latest post | latest_post = {self.latest_post}'

        # Scramble the check post ids for good measure
        self.check_post_ids[0] = 353

        self.__logger.info(f'Creating new forum monitor...')
        type(ForumMonitor)()

        # Restart forum monitor
        # Initial conditions and overides
        ForumMonitor._ForumMonitor__check_rate      = Threaded(0.1)
        ForumMonitor._ForumMonitor__latest_post_id  = Threaded(None)

        # Should be 2 as post id #2 is latest one checked before forum monitor restarted
        assert self.latest_post == 2

        # Should be 1 id to check as initial condition
        assert len(self.check_post_ids) == 1, f'Unexpected number of post ids to be checked | check_post_ids = {self.check_post_ids}'

        # Should be 3 as post id #2 is latest one checked before forum monitor restarted
        assert self.check_post_ids[0] == 3, f'Unexpected post id to check for | check_post_ids = {self.check_post_ids}'
