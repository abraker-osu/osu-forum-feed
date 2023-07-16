import pytest

import logging
import time

from core.SessionMgr import SessionMgr


class TestParsing:

    def setup_class(cls):
        cls.logger = logging.getLogger('TestParsing')
        print('Initializing Session Manager...')
        cls.session_mgr = SessionMgr()
        time.sleep(1)


    @classmethod
    def teardown_class(cls):
        print('Closing Session Manager...')
        cls.session_mgr.__del__()
        time.sleep(1)


    def test_post_parsing(self):
        print('\tGetting post...')
        start = time.time()
        post = self.session_mgr.get_post(6737014)
        print(f'\tGot post in {time.time() - start}s')
        time.sleep(1)

        expected_values = {
            'post_url'  : 'https://osu.ppy.sh/community/forums/posts/6737014',
            'post_id'   : '6737014',
            'post_date' : '2018-07-19 22:20:25+00:00',
            'post_text' : 'damn those americans',
            'post_num'  : '52030'
        }

        def read_post_url_test():  post_url = post.url;            assert str(post_url)  == expected_values['post_url']
        def read_post_id_test():   post_id = post.id;              assert str(post_id)   == expected_values['post_id']
        def read_post_date_test(): post_date = post.date;          assert str(post_date) == expected_values['post_date']
        def read_post_text_test(): post_text = post.contents_text; assert str(post_text) == expected_values['post_text']
        def read_post_number():    post_num = post.post_num;       assert str(post_num)  == expected_values['post_num']

        print('\t\tStarting read_post_url_test...')
        start = time.time()
        read_post_url_test()
        print(f'\t\tread_post_url_test completed in {time.time() - start}s')

        print('\t\tStarting read_post_id_test...')
        start = time.time()
        read_post_id_test()
        print(f'\t\ttread_post_id_test completed in {time.time() - start}s')

        print('\t\tStarting read_post_date_test...')
        start = time.time()
        read_post_date_test()
        print(f'\t\tread_post_date_test completed in {time.time() - start}s')

        print('\t\tStarting read_post_text_test...')
        start = time.time()
        read_post_text_test()
        print(f'\t\tread_post_text_test completed in {time.time() - start}s')

        print('\t\tStarting read_post_number...')
        start = time.time()
        read_post_number()
        print(f'\t\tread_post_number completed in {time.time() - start}s')


    def test_post_prev_next(self):
        print('\tGetting post...')
        start = time.time()
        post = self.session_mgr.get_post(6737014)
        print(f'\tGot post in {time.time() - start}s')
        time.sleep(1)

        print('\tGetting previous post...')
        start = time.time()
        prev_post = self.session_mgr.get_prev_post(post)
        print(f'\tGot previous post in {time.time() - start}s')
        time.sleep(1)

        assert str(prev_post.id) == '6737001', 'Next post ID not what expected!'

        print('\tGetting next post...')
        start = time.time()
        next_post = self.session_mgr.get_next_post(post)
        print(f'\tGot next post in {time.time() - start}s')
        time.sleep(1)

        assert str(next_post.id) == '6737045', 'Next post ID not what expected!'
