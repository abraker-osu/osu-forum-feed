import pytest

import logging
import time

import yaml

from core.SessionMgrV2 import SessionMgrV2


class TestParsing:

    def setup_class(cls):
        cls.logger = logging.getLogger('TestParsing')
        cls.logger.setLevel(logging.DEBUG)

        cls.logger.info('Initializing Session Manager...')
        cls.session_mgr = SessionMgrV2()

        with open('config.yaml', 'r') as f:
            cls.config = yaml.safe_load(f)
        time.sleep(1)


    @classmethod
    def teardown_class(cls):
        ...


    def test_topic_parsing(self):
        self.logger.info('Getting topic...')
        start = time.time()
        topic = self.session_mgr.get_thread(76484)
        self.logger.info(f'Got topic in {time.time() - start}s')
        time.sleep(1)

        expected_values = {
            'subforum_id'      : '52',
            'subforum_name'    : 'Off-Topic',
            'topic_date'       : '2012-03-04 14:24:59+00:00',
            'topic_name'       : 'ITT: we post things that are neither funny nor interesting',
            'topic_url'        : 'https://osu.ppy.sh/community/forums/topics/76484',
            'topic_id'         : '76484',
            'topic_post_count' : 14966
        }

        def read_subforum_id_test():      assert str(topic.subforum_id)   == expected_values['subforum_id']
        def read_subforum_name_test():    assert str(topic.subforum_name) == expected_values['subforum_name']
        def read_topic_date_test():       assert str(topic.date)          == expected_values['topic_date']
        def read_topic_name_test():       assert str(topic.name)          == expected_values['topic_name']
        def read_topic_url_test():        assert str(topic.url)           == expected_values['topic_url']
        def read_topic_id_test():         assert str(topic.id)            == expected_values['topic_id']
        def read_topic_post_count_test(): assert int(topic.post_count)    == expected_values['topic_post_count']

        self.logger.info('\t\tStarting read_subforum_id_test...')
        start = time.time()
        read_subforum_id_test()
        self.logger.info(f'\t\tread_subforum_id_test completed in {time.time() - start}s')

        self.logger.info('\t\tStarting read_subforum_name_test...')
        start = time.time()
        read_subforum_name_test()
        self.logger.info(f'\t\ttread_subforum_name_test completed in {time.time() - start}s')

        self.logger.info('\t\tStarting read_topic_date_test...')
        start = time.time()
        read_topic_date_test()
        self.logger.info(f'\t\tread_topic_date_test completed in {time.time() - start}s')

        self.logger.info('\t\tStarting read_topic_name_test...')
        start = time.time()
        read_topic_name_test()
        self.logger.info(f'\t\tread_topic_name_test completed in {time.time() - start}s')

        self.logger.info('\t\tStarting read_topic_url_test...')
        start = time.time()
        read_topic_url_test()
        self.logger.info(f'\t\tread_topic_url_test completed in {time.time() - start}s')

        self.logger.info('\t\tStarting read_topic_id_test...')
        start = time.time()
        read_topic_id_test()
        self.logger.info(f'\t\tread_topic_id_test in {time.time() - start}s')

        self.logger.info('\t\tStarting read_topic_post_count_test...')
        start = time.time()
        read_topic_post_count_test()
        self.logger.info(f'\t\tread_topic_post_count_test in {time.time() - start}s')


    def test_post_parsing(self):
        self.logger.info('\tGetting post...')
        start = time.time()
        post = self.session_mgr.get_post(6737014)
        self.logger.info(f'\tGot post in {time.time() - start}s')
        time.sleep(1)

        expected_values = {
            'post_url'  : 'https://osu.ppy.sh/community/forums/posts/6737014',
            'post_id'   : '6737014',
            'post_date' : '2018-07-19 22:20:25+00:00',
            'post_text' : 'damn those americans',
            'post_num'  : '52030'
        }

        def read_post_url_test():  post_url  = post.url;           assert str(post_url)  == expected_values['post_url']
        def read_post_id_test():   post_id   = post.id;            assert str(post_id)   == expected_values['post_id']
        def read_post_date_test(): post_date = post.date;          assert str(post_date) == expected_values['post_date']
        def read_post_text_test(): post_text = post.contents_text; assert str(post_text) == expected_values['post_text']
        def read_post_number():    post_num  = post.post_num;      assert str(post_num)  == expected_values['post_num']

        self.logger.info('\t\tStarting read_post_url_test...')
        start = time.time()
        read_post_url_test()
        self.logger.info(f'\t\tread_post_url_test completed in {time.time() - start}s')

        self.logger.info('\t\tStarting read_post_id_test...')
        start = time.time()
        read_post_id_test()
        self.logger.info(f'\t\ttread_post_id_test completed in {time.time() - start}s')

        self.logger.info('\t\tStarting read_post_date_test...')
        start = time.time()
        read_post_date_test()
        self.logger.info(f'\t\tread_post_date_test completed in {time.time() - start}s')

        self.logger.info('\t\tStarting read_post_text_test...')
        start = time.time()
        read_post_text_test()
        self.logger.info(f'\t\tread_post_text_test completed in {time.time() - start}s')

        self.logger.info('\t\tStarting read_post_number...')
        start = time.time()
        read_post_number()
        self.logger.info(f'\t\tread_post_number completed in {time.time() - start}s')


    def test_post_prev_next(self):
        self.logger.info('\tGetting post...')
        start = time.time()
        post = self.session_mgr.get_post(6737014)
        self.logger.info(f'\tGot post in {time.time() - start}s')
        time.sleep(1)

        self.logger.info('\tGetting previous post...')
        start = time.time()
        prev_post = self.session_mgr.get_prev_post(post)
        self.logger.info(f'\tGot previous post in {time.time() - start}s')
        time.sleep(1)

        assert str(prev_post.id) == '6737001', 'Next post ID not what expected!'

        self.logger.info('\tGetting next post...')
        start = time.time()
        next_post = self.session_mgr.get_next_post(post)
        self.logger.info(f'\tGot next post in {time.time() - start}s')
        time.sleep(1)

        assert str(next_post.id) == '6737045', 'Next post ID not what expected!'


    @pytest.mark.login
    def test_post_bbcode_parsing(self):
        self.session_mgr.login(self.config['Core']['web_username'], self.config['Core']['web_password'])

        self.logger.info('\tGetting bbcode from post...')
        start = time.time()
        bbcode = self.session_mgr.get_post_bbcode(6802486)
        self.logger.info(f'\tGot post in {time.time() - start}s')
        time.sleep(1)

        expected_bbcode = '[b]bold[/b] [i]italic[/i] [u]underline[/u] [strike]strike[/strike] [color=#0000FF]blue[/color]'
        assert str(bbcode) == expected_bbcode, 'BBCode not what expected!'


    @pytest.mark.login
    def test_edit_post_overwrite(self):
        self.session_mgr.login(
            self.config['Core']['api_client_id'],
            self.config['Core']['api_client_secret'],
            self.config['Core']['mailtrap_api_token'],
            self.config['Core']['mailtrap_addr_src'],
            self.config['Core']['email_addr_dst']
        )

        for i in range(5):
            self.logger.info(f'\tRun {i + 1} of 5...')

            self.logger.info('\tEditing post by bot owner (overwrite)...')
            start = time.time()
            self.session_mgr.edit_post(6630155, '1', append=False)
            self.logger.info(f'\tEdit completed in {time.time() - start} s')
            time.sleep(1)

            self.logger.info('\tReading post...')
            start = time.time()
            post = self.session_mgr.get_post(6630155)
            self.logger.info(f'\tPost read in {time.time() - start}s')
            time.sleep(1)

            post_contents = post.contents_text
            self.logger.info(f'\tPost contents: {post_contents}')

            value = int(post_contents)

            self.logger.info('\tEditing post by bot owner (overwrite)...')
            start = time.time()
            self.session_mgr.edit_post(6630155, str(value + 1), append=False)
            self.logger.info(f'\tEdit completed in {time.time() - start}s')
            time.sleep(1)

            self.logger.info('\tReading back post...')
            start = time.time()
            post = self.session_mgr.get_post(6630155)
            self.logger.info(f'\tPost read in {time.time() - start}s')
            time.sleep(1)

            post_contents = post.contents_text
            self.logger.info(f'\tPost contents: {post_contents}')

            assert int(post_contents) == value + 1, 'Post not edited!'


    @pytest.mark.login
    def test_edit_post_append(self):
        self.logger.info('\tSetting up initial condition...')
        self.session_mgr.login(
            self.config['Core']['api_client_id'],
            self.config['Core']['api_client_secret'],
            self.config['Core']['mailtrap_api_token'],
            self.config['Core']['mailtrap_addr_src'],
            self.config['Core']['email_addr_dst']
        )

        self.session_mgr.edit_post(6630155, '0000000', append=False)

        post_contents = self.session_mgr.get_post(6630155).contents_text
        assert post_contents == '0000000', f'Post not edited! Expected value: 0000000; Actual value: {post_contents}'

        for i in range(1, 5):
            self.logger.info(f'\tRun {i + 1} of 5...')

            self.logger.info('\tEditing post by bot owner (append)...')
            start = time.time()
            self.session_mgr.edit_post(6630155, str(i), append=True)
            self.logger.info(f'\tEdit completed in {time.time() - start}s')
            time.sleep(3)

            self.logger.info('\tReading post...')
            start = time.time()
            post = self.session_mgr.get_post(6630155)
            self.logger.info(f'\tPost read in {time.time() - start}s')
            time.sleep(3)

            post_contents = post.contents_text
            self.logger.info(f'\tPost contents: {post_contents}')

            expected_value = '0000000' + ''.join([ str(c) for c in range(1, i + 1) ])
            assert post_contents == expected_value, f'Post not edited! Expected value: {expected_value}'
