import pytest

import logging
import time

from core.SessionMgrV1 import SessionMgrV1


class TestSessionV1:

    __logger = logging.getLogger(__qualname__)

    def setup_class(cls):
        cls.__logger.setLevel(logging.DEBUG)


    @classmethod
    def teardown_class(cls):
        ...


    def test_sessionV1_web_read(self):
        start = time.time()
        SessionMgrV1.fetch_web_data('https://osu.ppy.sh/community/forums/topics/145250/?n=0')
        self.__logger.info(f'Got webpage in {time.time() - start}s')

        assert SessionMgrV1.get_last_status_code() == 200


    @pytest.mark.skip('No longer supported')
    @pytest.mark.login
    def test_sessionV1_login(self):
        SessionMgrV1.login()
