import pytest

import logging
import time

import yaml

from core.SessionMgrV1 import SessionMgrV1


class TestSessionV1:

    def setup_class(cls):
        cls.logger = logging.getLogger('TestSession')
        cls.logger.setLevel(logging.DEBUG)

        with open('config.yaml', 'r') as f:
            cls.config = yaml.safe_load(f)
        time.sleep(1)


    @classmethod
    def teardown_class(cls):
        ...


    def test_sessionV1_web_read(self):
        session_mgr = SessionMgrV1()

        start = time.time()
        session_mgr.fetch_web_data('https://osu.ppy.sh/community/forums/topics/145250/?n=0')
        self.logger.info(f'Got webpage in {time.time() - start}s')

        assert session_mgr.get_last_status_code() == 200
        session_mgr.__del__()


    @pytest.mark.login
    def test_sessionV1_login(self):
        session_mgr = SessionMgrV1()
        session_mgr.login(self.config['Core']['web_username'], self.config['Core']['web_password'])
        session_mgr.__del__()
