import pytest

import logging
import time

import yaml

from core.SessionMgrV2 import SessionMgrV2



class TestSessionV2:

    def setup_class(cls):
        cls.logger = logging.getLogger('TestSession')
        cls.logger.setLevel(logging.DEBUG)

        with open('config.yaml', 'r') as f:
            cls.config = yaml.safe_load(f)
        time.sleep(1)


    @classmethod
    def teardown_class(cls):
        ...


    def test_sessionV2_web_read(self):
        session_mgr = SessionMgrV2()

        start = time.time()
        session_mgr.fetch_web_data('https://osu.ppy.sh/community/forums/topics/145250/?n=0')
        self.logger.info(f'Got webpage in {time.time() - start}s')

        assert session_mgr.get_last_status_code() == 200
        session_mgr.__del__()


    @pytest.mark.login
    def test_sessionV2_login(self):
        session_mgr = SessionMgrV2()
        session_mgr.login(
            self.config['Core']['api_client_id'],
            self.config['Core']['api_client_secret'],
            self.config['Core']['mailtrap_api_token'],
            self.config['Core']['mailtrap_addr_src'],
            self.config['Core']['email_addr_dst']
        )
        session_mgr.__del__()
