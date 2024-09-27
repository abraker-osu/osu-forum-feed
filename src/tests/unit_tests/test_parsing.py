import pytest

import logging
import time

from core.SessionMgrV2 import SessionMgrV2
from core.parser import Post, Topic


class TestParsing:

    __logger = logging.getLogger(__qualname__)

    def setup_class(cls):
        cls.__logger.setLevel(logging.DEBUG)


    @classmethod
    def teardown_class(cls):
        ...


    def test_topic_parsing(self):
        self.__logger.info('Getting topic...')
        start = time.time()
        topic: Topic = SessionMgrV2.get_thread(76484)
        self.__logger.info(f'Got topic in {(time.time() - start)*1000:.3f}ms')
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

        self.__logger.info('\t\tStarting read_subforum_id_test...')
        start = time.time()
        read_subforum_id_test()
        self.__logger.info(f'\t\tread_subforum_id_test completed in {(time.time() - start)*1000:.3f}ms')

        self.__logger.info('\t\tStarting read_subforum_name_test...')
        start = time.time()
        read_subforum_name_test()
        self.__logger.info(f'\t\ttread_subforum_name_test completed in {(time.time() - start)*1000:.3f}ms')

        self.__logger.info('\t\tStarting read_topic_date_test...')
        start = time.time()
        read_topic_date_test()
        self.__logger.info(f'\t\tread_topic_date_test completed in {(time.time() - start)*1000:.3f}ms')

        self.__logger.info('\t\tStarting read_topic_name_test...')
        start = time.time()
        read_topic_name_test()
        self.__logger.info(f'\t\tread_topic_name_test completed in {(time.time() - start)*1000:.3f}ms')

        self.__logger.info('\t\tStarting read_topic_url_test...')
        start = time.time()
        read_topic_url_test()
        self.__logger.info(f'\t\tread_topic_url_test completed in {(time.time() - start)*1000:.3f}ms')

        self.__logger.info('\t\tStarting read_topic_id_test...')
        start = time.time()
        read_topic_id_test()
        self.__logger.info(f'\t\tread_topic_id_test in {(time.time() - start)*1000:.3f}ms')

        self.__logger.info('\t\tStarting read_topic_post_count_test...')
        start = time.time()
        read_topic_post_count_test()
        self.__logger.info(f'\t\tread_topic_post_count_test in {(time.time() - start)*1000:.3f}ms')


    def test_post_parsing(self):
        self.__logger.info('\tGetting post...')
        start = time.time()
        post: Post = SessionMgrV2.get_post(6737014)
        self.__logger.info(f'\tGot post {post.id} in {(time.time() - start)*1000:.3f}ms')
        time.sleep(1)

        expected_values = {
            'post_url'  : 'https://osu.ppy.sh/community/forums/posts/6737014',
            'post_id'   : '6737014',
            'post_date' : '2018-07-19 22:20:25+00:00',
            'post_text' : 'damn those americans',
            'post_num'  : '52030'
        }

        self.__logger.info('\t\tStarting read_post_url_test...')
        start = time.time()
        assert str(post.url) == expected_values['post_url']
        self.__logger.info(f'\t\tread_post_url_test completed in {(time.time() - start)*1000:.3f}ms')

        self.__logger.info('\t\tStarting read_post_id_test...')
        start = time.time()
        assert str(post.id) == expected_values['post_id']
        self.__logger.info(f'\t\ttread_post_id_test completed in {(time.time() - start)*1000:.3f}ms')

        self.__logger.info('\t\tStarting read_post_date_test...')
        start = time.time()
        assert str(post.date) == expected_values['post_date']
        self.__logger.info(f'\t\tread_post_date_test completed in {(time.time() - start)*1000:.3f}ms')

        self.__logger.info('\t\tStarting read_post_text_test...')
        start = time.time()
        assert str(post.contents_text) == expected_values['post_text']
        self.__logger.info(f'\t\tread_post_text_test completed in {(time.time() - start)*1000:.3f}ms')

        self.__logger.info('\t\tStarting read_post_number...')
        start = time.time()
        assert str(post.post_num) == expected_values['post_num']
        self.__logger.info(f'\t\tread_post_number completed in {(time.time() - start)*1000:.3f}ms')


    def test_post_prev_next(self):
        self.__logger.info('\tGetting post...')
        start = time.time()
        post: Post = SessionMgrV2.get_post(6737014)
        self.__logger.info(f'\tGot post in {(time.time() - start)*1000:.3f}ms')
        time.sleep(1)

        self.__logger.info('\tGetting previous post...')
        start = time.time()
        prev_post: Post = SessionMgrV2.get_prev_post(post)
        self.__logger.info(f'\tGot previous post in {(time.time() - start)*1000:.3f}ms')
        time.sleep(1)

        assert str(prev_post.id) == '6737001', 'Prev post ID not what expected!'

        self.__logger.info('\tGetting next post...')
        start = time.time()
        next_post = SessionMgrV2.get_next_post(post)
        self.__logger.info(f'\tGot next post in {(time.time() - start)*1000:.3f}ms')
        time.sleep(1)

        assert str(next_post.id) == '6737045', 'Next post ID not what expected!'


    @pytest.mark.skip('Not implemented yet')
    @pytest.mark.login
    def test_post_bbcode_parsing(self):
        self.__logger.info('\tGetting bbcode from post...')
        start = time.time()
        bbcode = SessionMgrV2.get_post_bbcode(6802486)
        self.__logger.info(f'\tGot post in {(time.time() - start)*1000:.3f}ms')
        time.sleep(1)

        expected_bbcode = '[b]bold[/b] [i]italic[/i] [u]underline[/u] [strike]strike[/strike] [color=#0000FF]blue[/color]'
        assert str(bbcode) == expected_bbcode, 'BBCode not what expected!'


    @pytest.mark.login
    def test_edit_post_overwrite(self):
        for i in range(5):
            self.__logger.info(f'\tRun {i + 1} of 5...')

            self.__logger.info('\tEditing post by bot owner (overwrite)...')
            start = time.time()
            SessionMgrV2.edit_post(6630155, '1', append=False)
            self.__logger.info(f'\tEdit completed in {time.time() - start} s')
            time.sleep(1)

            self.__logger.info('\tReading post...')
            start = time.time()
            post: Post = SessionMgrV2.get_post(6630155)
            self.__logger.info(f'\tPost read in {(time.time() - start)*1000:.3f}ms')
            time.sleep(1)

            post_contents = post.contents_text
            self.__logger.info(f'\tPost contents: {post_contents}')

            value = int(post_contents)

            self.__logger.info('\tEditing post by bot owner (overwrite)...')
            start = time.time()
            SessionMgrV2.edit_post(6630155, str(value + 1), append=False)
            self.__logger.info(f'\tEdit completed in {(time.time() - start)*1000:.3f}ms')
            time.sleep(1)

            self.__logger.info('\tReading back post...')
            start = time.time()
            post = SessionMgrV2.get_post(6630155)
            self.__logger.info(f'\tPost read in {(time.time() - start)*1000:.3f}ms')
            time.sleep(1)

            post_contents = post.contents_text
            self.__logger.info(f'\tPost contents: {post_contents}')

            assert int(post_contents) == value + 1, 'Post not edited!'


    @pytest.mark.login
    def test_edit_post_append(self):
        self.__logger.info('\tSetting up initial condition...')
        SessionMgrV2.edit_post(6630155, '0000000', append=False)

        post: Post = SessionMgrV2.get_post(6630155)
        assert post.contents_text == '0000000', f'Post not edited! Expected value: 0000000; Actual value: {post.contents_text}'

        for i in range(1, 5):
            self.__logger.info(f'\tRun {i + 1} of 5...')

            self.__logger.info('\tEditing post by bot owner (append)...')
            start = time.time()
            SessionMgrV2.edit_post(6630155, str(i), append=True)
            self.__logger.info(f'\tEdit completed in {(time.time() - start)*1000:.3f}ms')
            time.sleep(3)

            self.__logger.info('\tReading post...')
            start = time.time()
            post = SessionMgrV2.get_post(6630155)
            self.__logger.info(f'\tPost read in {(time.time() - start)*1000:.3f}ms')
            time.sleep(3)

            post_contents = post.contents_text
            self.__logger.info(f'\tPost contents: {post_contents}')

            expected_value = '0000000' + ''.join([ str(c) for c in range(1, i + 1) ])
            assert post_contents == expected_value, f'Post not edited! Expected value: {expected_value}'
