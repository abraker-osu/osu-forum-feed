import pytest

import logging
import time

import requests
import yaml

from core.SessionMgrV2 import SessionMgrV2



class TestSessionV2:

    __logger = logging.getLogger(__qualname__)

    def setup_class(cls):
        cls.__logger.setLevel(logging.DEBUG)


    @classmethod
    def teardown_class(cls):
        ...


    def test_sessionV2_web_read(self):
        start = time.time()
        SessionMgrV2.fetch_web_data('https://osu.ppy.sh/community/forums/topics/145250/?n=0')
        self.__logger.info(f'Got webpage in {(time.time() - start)*1000:.3f}ms')

        assert SessionMgrV2.get_last_status_code() == 200


    @pytest.mark.login
    def test_sessionV2_login(self):
        try: SessionMgrV2.login()
        except requests.ConnectionError as e:
            assert False, e
