import pytest

import os
import time
import logging
import datetime
import random

from core.BotConfig import BotConfig
from api.Cmd import Cmd

from bots.ThreadNecroBot import ThreadNecroBot


# Override botconfig settings
BotConfig['Core'].update({
    'is_dbg'      : True,
    'db_path_dbg' : 'db/test',
    'bots_path'   : 'src/bots',

    'discord_admin_user_id' : 1234
})



class ThreadNecroBotTest(ThreadNecroBot):

    # So that it doesn't actually post to forum
    def process_post(self):
        top_10_all_time_text     = self.get_top_10_text(self.DB_TYPE_ALLTIME)
        top_scores_all_time_text = self.get_top_scores_text(self.DB_TYPE_ALLTIME)
        log_all_time_text        = self.get_forum_log_text(self.DB_TYPE_ALLTIME)

        top_10_monthly_text     = self.get_top_10_text(self.DB_TYPE_MONTHLY)
        top_scores_monthly_text = self.get_top_scores_text(self.DB_TYPE_MONTHLY)
        log_monthly_text        = self.get_forum_log_text(self.DB_TYPE_MONTHLY)

        monthly_winners_text    = self.get_monthly_winners_text()

        # \TODO: Investigate the total score mismatching for same user
        # For the user [Taiga] the score went down by some amount from before to after when the score is only added
        # Screenshot: https://i.imgur.com/FSHCYW4.png
        # This may have some possible relation to username switching, however that should not be the case because the system uses user ids

        post_format = (
            '[notice]The rules are simple:\n'
            '[b][color=#008000]Points are awarded based on how long it has been since the last post was made.[/color]\n'
            '[color=#FF8B00]If you multi-post, you will loose 100 points[/color]\n'
            '[color=#FF4000]If you delete your post, your points will be halved[/color][/b]\n'
            '\n'
            'You can have your post contain whatever you want, so long it is within the forum-wide rules.\n'
            'Timing your posts is crucial as others can steal your points from you.'
            '\n'
            '[box=Scoring formula][centre][img]https://i.imgur.com/zJ7xjSL.png[/img][/centre][/box]\n'
            'If scoreboards are not updated for some time, shoot me a pm saying to update the scoreboard.\n'
            '\n'
            '[box=All-Time]'
            '[centre][b]Top 10 All-Time:[/b][/centre]'
            '[code]{0}[/code]\n'
            '\n'
            '[centre][b]Top Scores All-time Gained:[/b][/centre]'
            '[code]{1}[/code]\n'
            '\n'
            '[centre][b]All-time Score Log:[/b][/centre]'
            '[code]{2}[/code][/box]'
            '\n'
            '[centre][b]Top 10 Monthly:[/b][/centre]'
            '[code]{3}[/code]\n'
            '\n'
            '[centre][b]Top Monthly Scores Gained:[/b][/centre]'
            '[code]{4}[/code]\n'
            '\n'
            '[centre][b]Monthly Score Log:[/b][/centre]'
            '[code]{5}[/code]'
            '\n'
            '[centre][b]Monthly Winners:[/b][/centre]'
            '[code]{6}[/code][/notice]'
        )

        post_content = post_format.format(
            top_10_all_time_text,
            top_scores_all_time_text,
            log_all_time_text,
            top_10_monthly_text,
            top_scores_monthly_text,
            log_monthly_text,
            monthly_winners_text
        )
        return post_content



class TestNecroBot:

    __logger = logging.getLogger(__qualname__)

    @classmethod
    def setup_class(cls):
        cls.__logger.setLevel(logging.DEBUG)


    def setup_method(self, method):
        self.__logger.info('Creating new ThreadNecroBotTest...')

        BotConfig['ThreadNecroBot'].update({
            'post_id'  :  BotConfig['ThreadNecroBot']['post_id_dbg'],
            'topic_id' :  BotConfig['ThreadNecroBot']['topic_id_dbg'],
        })

        self.bot = ThreadNecroBotTest()
        self.__del_db()
        self.bot.post_init()


    def teardown_method(self, method):
        """
        Reset the database after each test to start each test clean
        """
        self.bot.stop()
        self.__del_db()


    def __del_db(self):
        time_start = time.time()

        db_files = [
            self.bot._ThreadNecroBotCore__DB_FILE_LOGS,
            self.bot._ThreadNecroBotCore__DB_FILE_WINNERS,
            self.bot._ThreadNecroBotCore__DB_FILE_SCORES,
            self.bot._ThreadNecroBotCore__DB_FILE_USERS,
            self.bot._ThreadNecroBotCore__DB_FILE_META,
        ]

        for db_file in db_files:
            while True:
                try:
                    os.remove(f'{BotConfig["Core"]["db_path_dbg"]}/{db_file}')
                    self.__logger.info(f'Deleted {BotConfig["Core"]["db_path_dbg"]}/{db_file}...')
                except PermissionError:
                    time.sleep(0.1)

                    if time.time() - time_start > 1:
                        pytest.fail(f'Failed to delete db - something is using it.')
                except FileNotFoundError:
                    break


    def test_update_user_data_all_time(self):
        """
        Tests the data in all_time being written to and from correctly
        """
        user_points = self.bot.get_user_points(1, self.bot.DB_TYPE_ALLTIME)
        assert user_points == 0, 'user_points is wrong'

        data_1 = {
            'added_score' : 1111,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1'
        }
        self.bot.update_user_data(data_1)

        # Check the user - should have 1111 pts, ranking #1 all time
        user_points = self.bot.get_user_points(data_1['user_id'], self.bot.DB_TYPE_ALLTIME)
        assert user_points == 1111, 'user_points is wrong'

        user_rank = self.bot.get_user_rank(data_1['user_id'], self.bot.DB_TYPE_ALLTIME)
        assert user_rank == 1, 'user_rank is wrong'

        # Add another post from same user
        self.bot.update_user_data(data_1)

        # Check the user - should have 2222 pts, ranking #1 all time
        user_points = self.bot.get_user_points(data_1['user_id'], self.bot.DB_TYPE_ALLTIME)
        assert user_points == 2222, 'user_points is wrong'

        user_rank = self.bot.get_user_rank(data_1['user_id'], self.bot.DB_TYPE_ALLTIME)
        assert user_rank == 1, 'user_rank is wrong'

        # Now lets do another user
        data_2 = {
            'added_score' : 9999,
            'user_id'     : 2,
            'post_id'     : 123456,
            'user_name'   : 'test user 2'
        }
        self.bot.update_user_data(data_2)

        # Check the new user - should have 9999 pts, ranking #1 all time
        user_points = self.bot.get_user_points(data_2['user_id'], self.bot.DB_TYPE_ALLTIME)
        assert user_points == 9999, 'user_points is wrong'

        user_rank = self.bot.get_user_rank(data_2['user_id'], self.bot.DB_TYPE_ALLTIME)
        assert user_rank == 1, 'user_rank is wrong'

        # Check the old user - should have 2222 pts, ranking #2 all time
        user_points = self.bot.get_user_points(data_1['user_id'], self.bot.DB_TYPE_ALLTIME)
        assert user_points == 2222, 'user_points is wrong'

        user_rank = self.bot.get_user_rank(data_1['user_id'], self.bot.DB_TYPE_ALLTIME)
        assert user_rank == 2, 'user_rank is wrong'


    def test_update_user_data_monthly(self):
        """
        Tests the data in monthly being written to and from correctly
        """
        user_points = self.bot.get_user_points(1, self.bot.DB_TYPE_MONTHLY)
        assert user_points == 0, 'user_points is wrong'

        data_1 = {
            'added_score' : 1111,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1'
        }
        self.bot.update_user_data(data_1)

        # Check the user - should have 1111 pts, ranking #1 monthly
        user_points = self.bot.get_user_points(data_1['user_id'], self.bot.DB_TYPE_MONTHLY)
        assert user_points == 1111, 'user_points is wrong'

        user_rank = self.bot.get_user_rank(data_1['user_id'], self.bot.DB_TYPE_MONTHLY)
        assert user_rank == 1, 'user_rank is wrong'

        # Add another post from same user
        self.bot.update_user_data(data_1)

        # Check the user - should have 2222 pts, ranking #1 monthly
        user_points = self.bot.get_user_points(data_1['user_id'], self.bot.DB_TYPE_MONTHLY)
        assert user_points == 2222, 'user_points is wrong'

        user_rank = self.bot.get_user_rank(data_1['user_id'], self.bot.DB_TYPE_MONTHLY)
        assert user_rank == 1, 'user_rank is wrong'

        # Now lets do another user
        data_2 = {
            'added_score' : 9999,
            'user_id'     : 2,
            'post_id'     : 123456,
            'user_name'   : 'test user 2'
        }
        self.bot.update_user_data(data_2)

        # Check the new user - should have 9999 pts, ranking #1 monthly (overtaking other player)
        user_points = self.bot.get_user_points(data_2['user_id'], self.bot.DB_TYPE_MONTHLY)
        assert user_points == 9999, 'user_points is wrong'

        user_rank = self.bot.get_user_rank(data_2['user_id'], self.bot.DB_TYPE_MONTHLY)
        assert user_rank == 1, 'user_rank is wrong'

        # Check the old user - should have 2222 pts (unchanged), ranking #2 monthly (being overtaken by the other player)
        user_points = self.bot.get_user_points(data_1['user_id'], self.bot.DB_TYPE_MONTHLY)
        assert user_points == 2222, 'user_points is wrong'

        user_rank = self.bot.get_user_rank(data_1['user_id'], self.bot.DB_TYPE_MONTHLY)
        assert user_rank == 2, 'user_rank is wrong'


    def test_update_user_data_all_time_monthly(self):
        """
        Tests the data in all_time and monthly being written to the correct selection
        """
        # Ranking:
        #   uid    all time   monthly
        #   1      1111       1111
        data_1 = {
            'added_score' : 1111,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1'
        }
        self.bot.update_user_data(data_1)

        # Check user - should have 1111 pts, and rank #1 monthly
        user_points = self.bot.get_user_points(data_1['user_id'], self.bot.DB_TYPE_MONTHLY)
        assert user_points == 1111, 'user_points is wrong'

        user_rank = self.bot.get_user_rank(data_1['user_id'], self.bot.DB_TYPE_MONTHLY)
        assert user_rank == 1, 'user_rank is wrong'

        # Check user - should have 1111 pts (got applied to all time), and rank #1 all time (got applied to all time)
        user_points = self.bot.get_user_points(data_1['user_id'], self.bot.DB_TYPE_ALLTIME)
        assert user_points == 1111, 'user_points is wrong'

        user_rank = self.bot.get_user_rank(data_1['user_id'], self.bot.DB_TYPE_ALLTIME)
        assert user_rank == 1, 'user_rank is wrong'

        # Check user - user id 2 all time should be empty
        user_points = self.bot.get_user_points(2, self.bot.DB_TYPE_ALLTIME)
        assert user_points == 0, 'user_points is wrong'

        # Ranking:
        #   uid    all time   monthly
        #   1      1111       1111
        #   2      9999       9999
        data_2 = {
            'added_score' : 9999,
            'user_id'     : 2,
            'post_id'     : 123456,
            'user_name'   : 'test user 2'
        }
        self.bot.update_user_data(data_2)

        # Check new user - should have 9999 pts, and rank #1 all time (overtaking the other player)
        user_points = self.bot.get_user_points(data_2['user_id'], self.bot.DB_TYPE_ALLTIME)
        assert user_points == 9999, 'user_points is wrong'

        user_rank = self.bot.get_user_rank(data_2['user_id'], self.bot.DB_TYPE_ALLTIME)
        assert user_rank == 1, 'user_rank is wrong'

        # Check old user - should have 2222 pts (unchanged), and rank #1 monthly (unchanged)
        user_points = self.bot.get_user_points(data_1['user_id'], self.bot.DB_TYPE_MONTHLY)
        assert user_points == 1111, 'user_points is wrong'

        user_rank = self.bot.get_user_rank(data_1['user_id'], self.bot.DB_TYPE_MONTHLY)
        assert user_rank == 2, 'user_rank is wrong'

        # Check user - user id 2 monthly should be filled in
        user_points = self.bot.get_user_points(data_2['user_id'], self.bot.DB_TYPE_MONTHLY)
        assert user_points == 9999, 'user_points is wrong'


    def test_multi_post_detection(self):
        """
        Tests multi post detection
        """
        prev_post = {
            'prev_post_user_id' : 1,
            'prev_post_id'      : 123455,
            'prev_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 25)
        }
        curr_post = {
            'curr_post_id'      : 123456,
            'prev_post_id'      : 123455,
            'curr_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 25),
            'prev_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 24),
            'curr_user_id'      : 2,
            'prev_user_id'      : 1,
            'curr_user_name'    : 'test user 2',
            'prev_user_name'    : 'test user 1'
        }

        # Is not a multipost since prev_post['prev_user_id'] and curr_post['curr_user_id'] are different
        is_multi_post = self.bot.is_multi_post(prev_post, curr_post)
        assert is_multi_post is False, 'is_multi_post is wrong'

        prev_post = {
            'prev_post_user_id' : 1,
            'prev_post_id'      : 123456,
            'prev_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 25),
        }
        curr_post = {
            'curr_post_id'      : 123456,
            'prev_post_id'      : 123455,
            'curr_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 25),
            'prev_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 24),
            'curr_user_id'      : 1,
            'prev_user_id'      : 1,
            'curr_user_name'    : 'test user 1',
            'prev_user_name'    : 'test user 1'
        }

        # Is a multipost since prev_post['prev_user_id'] and curr_post['curr_user_id'] are same
        is_multi_post = self.bot.is_multi_post(prev_post, curr_post)
        assert is_multi_post is True, 'is_multi_post is wrong'


    def test_curr_user_score_calc(self):
        """
        Tests current user score calculation
        """
        # Test multipost - should be -100 pts
        prev_post = {
            'prev_post_user_id' : 1,
            'prev_post_id'      : 123456,
            'prev_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 25)
        }
        curr_post = {
            'curr_post_id'   : 123456,
            'prev_post_id'   : 123455,
            'curr_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 25),
            'prev_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 24),
            'curr_user_id'   : 1,
            'prev_user_id'   : 1,
            'curr_user_name' : 'test user 1',
            'prev_user_name' : 'test user 1'
        }
        added_score = self.bot.calculate_score_gained_curr_user(prev_post, curr_post)
        assert added_score == -100, 'added_score is wrong'

        # Test 0 sec point difference post - should be 0 pts
        prev_post = {
            'prev_post_user_id' : 1,
            'prev_post_id'      : 123455,
            'prev_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 25)
        }
        curr_post = {
            'curr_post_id'   : 123456,
            'prev_post_id'   : 123455,
            'curr_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 25),
            'prev_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 25),
            'curr_user_id'   : 2,
            'prev_user_id'   : 1,
            'curr_user_name' : 'test user 2',
            'prev_user_name' : 'test user 1'
        }
        added_score = self.bot.calculate_score_gained_curr_user(prev_post, curr_post)
        assert added_score == 0, 'added_score is wrong'

        # Test 1 sec point difference - should be ~0 pts
        prev_post = {
            'prev_post_user_id' : 1,
            'prev_post_id'      : 123455,
            'prev_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 24),
        }
        curr_post = {
            'curr_post_id'   : 123456,
            'prev_post_id'   : 123455,
            'curr_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 25),
            'prev_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 24),
            'curr_user_id'   : 2,
            'prev_user_id'   : 1,
            'curr_user_name' : 'test user 2',
            'prev_user_name' : 'test user 1'
        }
        added_score = self.bot.calculate_score_gained_curr_user(prev_post, curr_post)
        assert added_score == pytest.approx(0, abs=0.1), 'added_score is wrong'

        # Test 1 day point difference - should be 2000 pts
        prev_post = {
            'prev_post_user_id' : 1,
            'prev_post_id'      : 123456,
            'prev_post_time'    : datetime.datetime(2018, 7, 18, 22, 20, 25),
        }
        curr_post = {
            'curr_post_id'   : 123456,
            'prev_post_id'   : 123455,
            'curr_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 25),
            'prev_post_time' : datetime.datetime(2018, 7, 18, 22, 20, 25),
            'curr_user_id'   : 2,
            'prev_user_id'   : 1,
            'curr_user_name' : 'test user 2',
            'prev_user_name' : 'test user 1'
        }
        added_score = self.bot.calculate_score_gained_curr_user(prev_post, curr_post)
        assert added_score == pytest.approx(2000, abs=0.001), 'added_score is wrong'


    def test_deleted_post_detection(self):
        """
        Tests deleted post detection
        """
        # Should be detect as a deleted post since prev_post['prev_post_time'] and curr_post['prev_post_time'] don't match
        prev_post = {
            'prev_post_user_id' : 1,
            'prev_post_id'      : 123456,
            'prev_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 24),
        }
        curr_post = {
            'curr_post_id'   : 123456,
            'prev_post_id'   : 123455,
            'curr_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 25),
            'prev_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 23),
            'curr_user_id'   : 1,
            'prev_user_id'   : 1,
            'curr_user_name' : 'test user 1',
            'prev_user_name' : 'test user 1'
        }
        is_deleted_post = self.bot.is_deleted_post(prev_post, curr_post)
        assert is_deleted_post is True, 'is_deleted_post is wrong'

        # Should not be detect as a deleted post since prev_post['time'] and curr_post['prev_post_time'] do match
        prev_post = {
            'prev_post_user_id' : 1,
            'prev_post_id'      : 123456,
            'prev_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 23),
        }
        curr_post = {
            'curr_post_id'   : 123456,
            'prev_post_id'   : 123455,
            'curr_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 25),
            'prev_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 23),
            'curr_user_id'   : 1,
            'prev_user_id'   : 1,
            'curr_user_name' : 'test user 1',
            'prev_user_name' : 'test user 1'
        }
        is_deleted_post = self.bot.is_deleted_post(prev_post, curr_post)
        assert is_deleted_post is False, 'is_deleted_post is wrong'

        # TODO: Test special events


    def test_prev_user_score_calc(self):
        """
        Tests previous user score calculation
        """
        # Test deleted post - score starts with 0 -> added_score should be 0
        prev_post = {
            'prev_post_user_id' : 1,
            'prev_post_id'      : 123456,
            'prev_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 24),
        }
        curr_post = {
            'curr_post_id'   : 123456,
            'prev_post_id'   : 123455,
            'curr_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 25),
            'prev_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 23),
            'curr_user_id'   : 1,
            'prev_user_id'   : 1,
            'curr_user_name' : 'test user 1',
            'prev_user_name' : 'test user 1'
        }
        added_score = self.bot.calculate_score_gained_prev_user(prev_post, curr_post)
        assert added_score == 0, 'added_score is wrong'

        # Test deleted post - score starts with 100 -> added_score should be -|100/2| = -50
        self.bot.update_user_data({
            'added_score' : 100 - self.bot.get_user_points(1, self.bot.DB_TYPE_ALLTIME),
            'user_id'     : 1,
            'user_name'   : 'test user 1',
            'post_id'     : 123455
        })
        assert self.bot.get_user_points(1, self.bot.DB_TYPE_ALLTIME) == 100, 'user score is wrong'
        assert self.bot.get_user_points(1, self.bot.DB_TYPE_MONTHLY) == 100, 'user score is wrong'

        prev_post = {
            'prev_post_user_id' : 1,
            'prev_post_id'      : 123456,
            'prev_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 24),
        }
        curr_post = {
            'curr_post_id'   : 123456,
            'prev_post_id'   : 123455,
            'curr_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 25),
            'prev_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 23),
            'curr_user_id'   : 1,
            'prev_user_id'   : 1,
            'curr_user_name' : 'test user 1',
            'prev_user_name' : 'test user 1'
        }
        added_score = self.bot.calculate_score_gained_prev_user(prev_post, curr_post)
        assert added_score == -50, 'added_score is wrong'

        # Test deleted post - score starts with -100 -> added_score should be -|-100/2| = -50
        self.bot.update_user_data({
            'added_score' : -100 - self.bot.get_user_points(1, self.bot.DB_TYPE_ALLTIME),
            'user_id'     : 1,
            'user_name'   : 'test user 1',
            'post_id'     : 123455
        })
        assert self.bot.get_user_points(1, self.bot.DB_TYPE_ALLTIME) == -100, 'user score is wrong'
        assert self.bot.get_user_points(1, self.bot.DB_TYPE_MONTHLY) == -100, 'user score is wrong'

        prev_post = {
            'prev_post_user_id' : 1,
            'prev_post_id'      : 123456,
            'prev_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 24),
        }
        curr_post = {
            'curr_post_id'   : 123456,
            'prev_post_id'   : 123455,
            'curr_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 25),
            'prev_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 23),
            'curr_user_id'   : 1,
            'prev_user_id'   : 1,
            'curr_user_name' : 'test user 1',
            'prev_user_name' : 'test user 1'
        }
        added_score = self.bot.calculate_score_gained_prev_user(prev_post, curr_post)
        assert added_score == -50, 'added_score is wrong'

        # Test deleted post - score starts with -2000000000 -> added_score should be -1
        self.bot.update_user_data({
            'added_score' : -2000000000 - self.bot.get_user_points(1, self.bot.DB_TYPE_ALLTIME),
            'user_id'     : 1,
            'user_name'   : 'test user 1',
            'post_id'     : 123455
        })
        assert self.bot.get_user_points(1, self.bot.DB_TYPE_ALLTIME) == -2000000000, 'user score is wrong'
        assert self.bot.get_user_points(1, self.bot.DB_TYPE_MONTHLY) == -2000000000, 'user score is wrong'

        prev_post = {
            'prev_post_user_id' : 1,
            'prev_post_id'      : 123456,
            'prev_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 24),
        }
        curr_post = {
            'curr_post_id'   : 123456,
            'prev_post_id'   : 123455,
            'curr_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 25),
            'prev_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 23),
            'curr_user_id'   : 1,
            'prev_user_id'   : 1,
            'curr_user_name' : 'test user 1',
            'prev_user_name' : 'test user 1'
        }
        added_score = self.bot.calculate_score_gained_prev_user(prev_post, curr_post)
        assert added_score == -1, 'added_score is wrong'

        # Test deleted post - score starts with 2000000000 -> added_score should be -1000000000
        self.bot.update_user_data({
            'added_score' : 2000000000 - self.bot.get_user_points(1, self.bot.DB_TYPE_ALLTIME),
            'user_id'     : 1,
            'user_name'   : 'test user 1',
            'post_id'     : 123455
        })
        assert self.bot.get_user_points(1, self.bot.DB_TYPE_ALLTIME) == 2000000000, 'user score is wrong'
        assert self.bot.get_user_points(1, self.bot.DB_TYPE_MONTHLY) == 2000000000, 'user score is wrong'

        prev_post = {
            'prev_post_user_id' : 1,
            'prev_post_id'      : 123456,
            'prev_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 24),
        }
        curr_post = {
            'curr_post_id'   : 123456,
            'prev_post_id'   : 123455,
            'curr_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 25),
            'prev_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 23),
            'curr_user_id'   : 1,
            'prev_user_id'   : 1,
            'curr_user_name' : 'test user 1',
            'prev_user_name' : 'test user 1'
        }
        added_score = self.bot.calculate_score_gained_prev_user(prev_post, curr_post)
        assert added_score == -1000000000, 'added_score is wrong'

        # Test normal post - score starts with x -> added_score should be 0
        prev_post = {
            'prev_post_user_id' : 1,
            'prev_post_id'      : 123456,
            'prev_post_time'    : datetime.datetime(2018, 7, 19, 22, 20, 23),
        }
        curr_post = {
            'curr_post_id'   : 123456,
            'prev_post_id'   : 123455,
            'curr_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 25),
            'prev_post_time' : datetime.datetime(2018, 7, 19, 22, 20, 23),
            'curr_user_id'   : 1,
            'prev_user_id'   : 1,
            'curr_user_name' : 'test user 1',
            'prev_user_name' : 'test user 1'
        }
        added_score = self.bot.calculate_score_gained_prev_user(prev_post, curr_post)
        assert added_score == 0, 'added_score is wrong'


    def test_ranked_all_time(self):
        """
        Tests ranked list to return user points in the correct order and amount
        """
        # Add a bunch of random scores
        for i in range(100):
            data = {
                'added_score' : 100*random.random(),
                'user_id'     : i,
                'post_id'     : 10000 + i*10,
                'user_name'   : 'test user ' + str(i)
            }
            self.bot.update_user_data(data)

            ranked_list = self.bot.get_ranked_list(self.bot.DB_TYPE_ALLTIME)

            assert len(ranked_list) ==  i + 1, 'Ranked list does not have the expected number of entries'
            for i in range(len(ranked_list) - 1):
                assert ranked_list[i]['points'] > ranked_list[i + 1]['points'], f'#{i} pts are less than #{i + 1}'

        assert len(ranked_list) == 100, 'Ranked list does not have the expected number of entries'

        # Add a bunch of low scores
        for i in range(100):
            data = {
                'added_score' : 10*random.random(),
                'user_id'     : i,
                'post_id'     : 10000 + i*10,
                'user_name'   : 'test user ' + str(i)
            }
            self.bot.update_user_data(data)

            ranked_list = self.bot.get_ranked_list(self.bot.DB_TYPE_ALLTIME)
            for i in range(len(ranked_list) - 1):
                assert ranked_list[i]['points'] >= ranked_list[i + 1]['points'], f'#{i} pts are less than #{i + 1}'

        assert len(ranked_list) == 100, 'Ranked list does not have the expected number of entries'

        # Add a bunch of high scores
        for i in range(100):
            data = {
                'added_score' : 1000*random.random(),
                'user_id'     : i,
                'post_id'     : 10000 + i*10,
                'user_name'   : 'test user ' + str(i)
            }
            self.bot.update_user_data(data)

            ranked_list = self.bot.get_ranked_list(self.bot.DB_TYPE_ALLTIME)
            for i in range(len(ranked_list) - 1):
                assert ranked_list[i]['points'] >= ranked_list[i + 1]['points'], f'#{i} pts are less than #{i + 1}'


    def test_top_scores_all_time(self):
        """
        Tests top scores list
        """
        # Add a bunch of random scores
        for i in range(11):
            new_score_data = {
                'time'        : str(datetime.datetime(2018, 7, 19, 22, i, 25)),
                'user_id'     : str(i),
                'user_name'   : f'test user {i}',
                'post_id'     : str(10000 + i*10),
                'added_score' : '%.3f'%(100*random.random()),
            }
            self.bot.update_top_score_data(new_score_data)

            top_scores_list = self.bot.get_top_scores_list(self.bot.DB_TYPE_ALLTIME)
            for i in range(1, len(top_scores_list)):
                assert float(top_scores_list[i - 1]['added_score']) > float(top_scores_list[i]['added_score']), f'#{i - 1} place is less than #{i} place'

        assert len(top_scores_list) == 11, 'Top score list does not have the expected number of entries'

        # Add a bunch of low scores
        for i in range(100):
            new_score_data = {
                'time'        : str(datetime.datetime(2018, 7, 19, int(i/60)%24, i%60, 25)),
                'user_id'     : f'{i}',
                'user_name'   : f'test user {i}',
                'post_id'     : f'{10000 + i*10}',
                'added_score' : f'{10*random.random():.3f}',
                }
            self.bot.update_top_score_data(new_score_data)

            top_scores_list = self.bot.get_top_scores_list(self.bot.DB_TYPE_ALLTIME)
            for i in range(len(top_scores_list) - 1):
                assert float(top_scores_list[i]['added_score']) > float(top_scores_list[i + 1]['added_score']), f'#{i} pts are less than #{i + 1}'

        assert len(top_scores_list) == 100, 'Top score list does not have the expected number of entries'

        # Add a bunch of high scores
        for i in range(100):
            new_score_data = {
                'time'        : str(datetime.datetime(2018, 7, 19, int(i/60)%24, i%60, 25)),
                'user_id'     : str(i),
                'user_name'   : f'test user {i}',
                'post_id'     : str(10000 + i*10),
                'added_score' : '%.3f'%(1000*random.random()),
                }
            self.bot.update_top_score_data(new_score_data)

            top_scores_list = self.bot.get_top_scores_list(self.bot.DB_TYPE_ALLTIME)
            for i in range(len(top_scores_list) - 1):
                assert float(top_scores_list[i]['added_score']) > float(top_scores_list[i + 1]['added_score']), f'#{i} pts are less than #{i + 1}'

        assert len(top_scores_list) == 100, 'Top score list does not have the expected number of entries'


    def test_log_all_time(self):
        """
        Tests db logging
        """
        for i in range(20):
            user_score_all_time = self.bot.get_user_points(i, self.bot.DB_TYPE_ALLTIME)

            log_data = {
                'time'        : str(datetime.datetime(2018, 7, 19, 22, i, 25)),
                'user_name'   : str('test user ' + str(i)),
                'user_id'     : str(i),
                'post_id'     : str(10000 + i*10),
                'added_score' : '%.3f'%(100*random.random()),
                'total_score' : str(user_score_all_time)
            }
            self.bot.update_log_data(log_data)

        for i in range(20):
            log_list = self.bot.get_log_list(self.bot.DB_TYPE_ALLTIME, num = i)
            assert len(log_list) == i, f'Unexpected number of log entries: {len(log_list)} != {i}'

            for i in range(len(log_list) - 1):
                assert int(log_list[i]['post_id']) > int(log_list[i + 1]['post_id']), 'Log list should be sorted from oldest to newest'


    def test_50__cmd_add_user_points__user_points(self):
        """
        Tests player's points after doing the add_user_points command
        """
        for i in range(100):
            data = {
                'time'        : str(datetime.datetime.now()),
                'added_score' : 100*random.random(),
                'user_id'     : i,
                'post_id'     : 10000 + i*10,
                'user_name'   : 'test user ' + str(i)
            }
            self.bot.update_user_data(data)
            self.bot.update_log_data(data)

        # Test positive point addition to user
        test_user_50_pts_before = self.bot.get_user_points(50, self.bot.DB_TYPE_ALLTIME)

        bot_cmd = ThreadNecroBotTest.BotCmd(self.bot)
        print(bot_cmd.cmd_add_user_points['exec'](bot_cmd, 'test user 50', '123.456'))

        test_user_50_pts_after = self.bot.get_user_points(50, self.bot.DB_TYPE_ALLTIME)

        # Make sure the correct number of points got added - should be a 123.456 difference
        diff = test_user_50_pts_after - test_user_50_pts_before
        assert round(diff, 3) == 123.456, 'Score after does not match expected'

        # Test negative point addition to user
        test_user_50_pts_before = self.bot.get_user_points(50, self.bot.DB_TYPE_ALLTIME)

        bot_cmd = ThreadNecroBotTest.BotCmd(self.bot)
        print(bot_cmd.cmd_add_user_points['exec'](bot_cmd, 'test user 50', '-123.456'))

        test_user_50_pts_after = self.bot.get_user_points(50, self.bot.DB_TYPE_ALLTIME)

        # Make sure the correct number of points got added - should be a -123.456 difference
        diff = test_user_50_pts_after - test_user_50_pts_before
        assert round(diff, 3) == -123.456, 'Score after does not match expected'


    def test_cmd_add_user_points__ranked_sort(self):
        """
        Tests the ranked list after doing the add_user_points command
        """
        for i in range(100):
            data = {
                'added_score' : 100*random.random(),
                'user_id'     : i,
                'post_id'     : 10000 + i*10,
                'user_name'   : 'test user ' + str(i)
            }
            self.bot.update_user_data(data)

        bot_cmd = ThreadNecroBotTest.BotCmd(self.bot)
        print(bot_cmd.cmd_add_user_points['exec'](bot_cmd, 'test user 50', '1.23456'))

        # Make sure the ranked list is returned sorted correctly after invoking the add_user_points command
        ranked_list = self.bot.get_ranked_list(self.bot.DB_TYPE_ALLTIME)
        for i in range(len(ranked_list) - 1):
            assert ranked_list[i]['points'] >= ranked_list[i + 1]['points'], f'#{i} pts are less than #{i + 1}'

        assert len(ranked_list) == 100, 'Ranked list does not have the expected number of entries'

        ranked_list = self.bot.get_ranked_list(self.bot.DB_TYPE_MONTHLY)
        for i in range(len(ranked_list) - 1):
            assert ranked_list[i]['points'] >= ranked_list[i + 1]['points'], f'#{i} pts are less than #{i + 1}'

        assert len(ranked_list) == 100, 'Ranked list does not have the expected number of entries'
