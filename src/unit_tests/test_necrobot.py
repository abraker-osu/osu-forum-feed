import pytest

import tinydb
import logging
import datetime
import random
import config

from bots.ThreadNecroBot import ThreadNecroBot
from bots.ThreadNecroBotCore.ThreadNecroBotCore import DB_ENUM



class ThreadNecroBotTest:

    # So that it doesn't actually post to forum
    def process_post(self):
        top_10_all_time_text     = self.get_top_10_text(self.logger, db, self.get_top_10_list(self.logger, db, DB_ENUM.ALL_TIME))
        top_scores_all_time_text = self.get_top_scores_text(self.logger, self.get_top_scores_list(self.logger, db, DB_ENUM.ALL_TIME))
        log_all_time_text        = self.get_forum_log_text(self.logger, self.get_log_list(self.logger, db, DB_ENUM.ALL_TIME))

        top_10_monthly_text     = self.get_top_10_text(self.logger, db, self.get_top_10_list(self.logger, db, DB_ENUM.MONTHLY))
        top_scores_monthly_text = self.get_top_scores_text(self.logger, self.get_top_scores_list(self.logger, db, DB_ENUM.MONTHLY))
        log_monthly_text        = self.get_forum_log_text(self.logger, self.get_log_list(self.logger, db, DB_ENUM.MONTHLY))

        monthly_winners_text    = self.get_monthly_winners_text(self.logger, self.get_monthly_winners_list(self.logger, db))

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


@pytest.mark.skip('To implement')
class TestNecroBot:

    @classmethod
    def setUpClass(cls):
        cls.bot       = ThreadNecroBotTest(cls)
        cls.db_client = pymongo.MongoClient(config.mongo_address)
        cls.logger    = logging.getLogger('TestNecroBot')

        cls.get_db = lambda name: cls.db_client['forum-bot-test']['TestNecroBot_' + name]

        try: cls.db_client.drop_database('forum-bot-test')
        except: pass


    '''
    Reset the database after each test to start each test clean
    '''
    @classmethod
    def tearDown(cls):
        try: cls.db_client.drop_database('forum-bot-test')
        except: pass


    def test_db_name_get(self):
        name = self.bot.get_db(DB_ENUM.ALL_TIME, DB_ENUM.USER_DATA)
        self.assertEqual(name, 'UserData', 'Wrong DB name')
        name = self.bot.get_db_table(name).full_name
        self.assertEqual(name, 'forum-bot-test.TestNecroBot_ThreadNecroBotTest_UserData', 'Wrong DB name')

        name = self.bot.get_db(DB_ENUM.MONTHLY, DB_ENUM.USER_DATA)
        self.assertEqual(name, 'UserData_monthly', 'Wrong DB name')
        name = self.bot.get_db_table(name).full_name
        self.assertEqual(name, 'forum-bot-test.TestNecroBot_ThreadNecroBotTest_UserData_monthly', 'Wrong DB name')

        name = self.bot.get_db(DB_ENUM.ALL_TIME, DB_ENUM.TOP_SCORES)
        self.assertEqual(name, 'TopScoresData', 'Wrong DB name')
        name = self.bot.get_db_table(name).full_name
        self.assertEqual(name, 'forum-bot-test.TestNecroBot_ThreadNecroBotTest_TopScoresData', 'Wrong DB name')

        name = self.bot.get_db(DB_ENUM.MONTHLY, DB_ENUM.TOP_SCORES)
        self.assertEqual(name, 'TopScoresData_monthly', 'Wrong DB name')
        name = self.bot.get_db_table(name).full_name
        self.assertEqual(name, 'forum-bot-test.TestNecroBot_ThreadNecroBotTest_TopScoresData_monthly', 'Wrong DB name')

        name = self.bot.get_db(DB_ENUM.ALL_TIME, DB_ENUM.LOG_DATA)
        self.assertEqual(name, 'LogData', 'Wrong DB name')
        name = self.bot.get_db_table(name).full_name
        self.assertEqual(name, 'forum-bot-test.TestNecroBot_ThreadNecroBotTest_LogData', 'Wrong DB name')

        name = self.bot.get_db(DB_ENUM.MONTHLY, DB_ENUM.LOG_DATA)
        self.assertEqual(name, 'LogData_monthly', 'Wrong DB name')
        name = self.bot.get_db_table(name).full_name
        self.assertEqual(name, 'forum-bot-test.TestNecroBot_ThreadNecroBotTest_LogData_monthly', 'Wrong DB name')


    '''
    Tests the data in all_time being written to and from correctly
    '''
    def test_update_user_data_all_time(self):
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, 1, DB_ENUM.ALL_TIME)
        self.assertEqual(user_points, 0, 'user_points is wrong')

        data_1 = {
            'added_score' : 1111,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1'
        }
        self.bot.update_user_data(self.logger, self.bot.get_db_table, data_1, DB_ENUM.ALL_TIME)

        # Check the user - should have 1111 pts, ranking #1 all time
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.ALL_TIME)
        self.assertEqual(user_points, 1111, 'user_points is wrong')

        user_rank = self.bot.get_user_rank(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.ALL_TIME)
        self.assertEqual(user_rank, 1, 'user_rank is wrong')

        # Add another post from same user
        self.bot.update_user_data(self.logger, self.bot.get_db_table, data_1, DB_ENUM.ALL_TIME)

        # Check the user - should have 2222 pts, ranking #1 all time
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.ALL_TIME)
        self.assertEqual(user_points, 2222, 'user_points is wrong')

        user_rank = self.bot.get_user_rank(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.ALL_TIME)
        self.assertEqual(user_rank, 1, 'user_rank is wrong')

        # Now lets do another user
        data_2 = {
            'added_score' : 9999,
            'user_id'     : 2,
            'post_id'     : 123456,
            'user_name'   : 'test user 2'
        }
        self.bot.update_user_data(self.logger, self.bot.get_db_table, data_2, DB_ENUM.ALL_TIME)

        # Check the new user - should have 9999 pts, ranking #1 all time
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, data_2['user_id'], DB_ENUM.ALL_TIME)
        self.assertEqual(user_points, 9999, 'user_points is wrong')

        user_rank = self.bot.get_user_rank(self.logger, self.bot.get_db_table, data_2['user_id'], DB_ENUM.ALL_TIME)
        self.assertEqual(user_rank, 1, 'user_rank is wrong')

        # Check the old user - should have 2222 pts, ranking #2 all time
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.ALL_TIME)
        self.assertEqual(user_points, 2222, 'user_points is wrong')

        user_rank = self.bot.get_user_rank(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.ALL_TIME)
        self.assertEqual(user_rank, 2, 'user_rank is wrong')


    '''
    Tests the data in monthly being written to and from correctly
    '''
    def test_update_user_data_monthly(self):
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, 1, DB_ENUM.MONTHLY)
        self.assertEqual(user_points, 0, 'user_points is wrong')

        data_1 = {
            'added_score' : 1111,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1'
        }
        self.bot.update_user_data(self.logger, self.bot.get_db_table, data_1, DB_ENUM.MONTHLY)

        # Check the user - should have 1111 pts, ranking #1 monthly
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.MONTHLY)
        self.assertEqual(user_points, 1111, 'user_points is wrong')

        user_rank = self.bot.get_user_rank(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.MONTHLY)
        self.assertEqual(user_rank, 1, 'user_rank is wrong')

        # Add another post from same user
        self.bot.update_user_data(self.logger, self.bot.get_db_table, data_1, DB_ENUM.MONTHLY)

        # Check the user - should have 2222 pts, ranking #1 monthly
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.MONTHLY)
        self.assertEqual(user_points, 2222, 'user_points is wrong')

        user_rank = self.bot.get_user_rank(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.MONTHLY)
        self.assertEqual(user_rank, 1, 'user_rank is wrong')

        # Now lets do another user
        data_2 = {
            'added_score' : 9999,
            'user_id'     : 2,
            'post_id'     : 123456,
            'user_name'   : 'test user 2'
        }
        self.bot.update_user_data(self.logger, self.bot.get_db_table, data_2, DB_ENUM.MONTHLY)

        # Check the new user - should have 9999 pts, ranking #1 monthly (overtaking other player)
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, data_2['user_id'], DB_ENUM.MONTHLY)
        self.assertEqual(user_points, 9999, 'user_points is wrong')

        user_rank = self.bot.get_user_rank(self.logger, self.bot.get_db_table, data_2['user_id'], DB_ENUM.MONTHLY)
        self.assertEqual(user_rank, 1, 'user_rank is wrong')

        # Check the old user - should have 2222 pts (unchanged), ranking #2 monthly (being overtaken by the other player)
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.MONTHLY)
        self.assertEqual(user_points, 2222, 'user_points is wrong')

        user_rank = self.bot.get_user_rank(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.MONTHLY)
        self.assertEqual(user_rank, 2, 'user_rank is wrong')


    '''
    Tests the data in all_time and monthly being written to the correct selection
    '''
    def test_update_user_data_all_time_monthly(self):
        data_1 = {
            'added_score' : 1111,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1'
        }
        self.bot.update_user_data(self.logger, self.bot.get_db_table, data_1, DB_ENUM.MONTHLY)

        # Check user - should have 1111 pts, and rank #1 monthly
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.MONTHLY)
        self.assertEqual(user_points, 1111, 'user_points is wrong')

        user_rank = self.bot.get_user_rank(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.MONTHLY)
        self.assertEqual(user_rank, 1, 'user_rank is wrong')

        # Make sure adding data to all-time doesn't affect monthly data
        self.bot.update_user_data(self.logger, self.bot.get_db_table, data_1, DB_ENUM.ALL_TIME)

        # Check user - should have 1111 pts (got applied to all time), and rank #1 all time (got applied to all time)
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.ALL_TIME)
        self.assertEqual(user_points, 1111, 'user_points is wrong')

        user_rank = self.bot.get_user_rank(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.ALL_TIME)
        self.assertEqual(user_rank, 1, 'user_rank is wrong')

        # Make sure adding data to monthly doesn't affect all time
        self.bot.update_user_data(self.logger, self.bot.get_db_table, data_1, DB_ENUM.MONTHLY)

        # Check user - should still have 1111 pts (unaffected by monthly manipulation), and still rank #1 all time (unaffected by monthly manipulation)
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.ALL_TIME)
        self.assertEqual(user_points, 1111, 'user_points is wrong')

        user_rank = self.bot.get_user_rank(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.ALL_TIME)
        self.assertEqual(user_rank, 1, 'user_rank is wrong')

        # Check user - user id 2 all time should be empty
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, 2, DB_ENUM.ALL_TIME)
        self.assertEqual(user_points, 0, 'user_points is wrong')

        # Now lets do another user
        data_2 = {
            'added_score' : 9999,
            'user_id'     : 2,
            'post_id'     : 123456,
            'user_name'   : 'test user 2'
        }
        self.bot.update_user_data(self.logger, self.bot.get_db_table, data_2, DB_ENUM.ALL_TIME)

        # Check new user - should have 9999 pts, and rank #1 all time (overtaking the other player)
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, data_2['user_id'], DB_ENUM.ALL_TIME)
        self.assertEqual(user_points, 9999, 'user_points is wrong')

        user_rank = self.bot.get_user_rank(self.logger, self.bot.get_db_table, data_2['user_id'], DB_ENUM.ALL_TIME)
        self.assertEqual(user_rank, 1, 'user_rank is wrong')

        # Check old user - should have 2222 pts (unchanged), and rank #1 monthly (unchanged)
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.MONTHLY)
        self.assertEqual(user_points, 2222, 'user_points is wrong')

        user_rank = self.bot.get_user_rank(self.logger, self.bot.get_db_table, data_1['user_id'], DB_ENUM.MONTHLY)
        self.assertEqual(user_rank, 1, 'user_rank is wrong')

        # Check user - user id 2 monthly should still be empty
        user_points = self.bot.get_user_points(self.logger, self.bot.get_db_table, 2, DB_ENUM.MONTHLY)
        self.assertEqual(user_points, 0, 'user_points is wrong')


    '''
    Tests multi post detection
    '''
    def test_multi_post_detection(self):
        prev_post = {
            'total_score' : 0,
            'user_id'     : 1,
            'post_id'     : 123455,
            'user_name'   : 'test user 1',
            'time'        : datetime.datetime(2018, 7, 19, 22, 20, 25)
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

        # Is not a multipost since prev_post['user_id'] and curr_post['curr_user_id'] are different
        is_multi_post = self.bot.is_multi_post(self.logger, prev_post, curr_post)
        self.assertEqual(is_multi_post, False, 'is_multi_post is wrong')

        prev_post = {
            'total_score' : 0,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1',
            'time'        : datetime.datetime(2018, 7, 19, 22, 20, 25),
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

        # Is a multipost since prev_post['user_id'] and curr_post['curr_user_id'] are same
        is_multi_post = self.bot.is_multi_post(self.logger, prev_post, curr_post)
        self.assertEqual(is_multi_post, True, 'is_multi_post is wrong')


    '''
    Tests current user score calculation
    '''
    def test_curr_user_score_calc(self):
        # Test multipost - should be -100 pts
        prev_post = {
            'total_score' : 0,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1',
            'time'        : datetime.datetime(2018, 7, 19, 22, 20, 25),
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
        added_score = self.bot.calculate_score_gained_curr_user(self.logger, prev_post, curr_post)
        self.assertEqual(added_score, -100, 'added_score is wrong')

        # Test 0 sec point difference post - should be 0 pts
        prev_post = {
            'total_score' : 0,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1',
            'time'        : datetime.datetime(2018, 7, 19, 22, 20, 25),
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
        added_score = self.bot.calculate_score_gained_curr_user(self.logger, prev_post, curr_post)
        self.assertEqual(added_score, 0, 'added_score is wrong')

        # Test 1 sec point difference - should be ~0 pts
        prev_post = {
            'total_score' : 0,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1',
            'time'        : datetime.datetime(2018, 7, 19, 22, 20, 25),
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
        added_score = self.bot.calculate_score_gained_curr_user(self.logger, prev_post, curr_post)
        self.assertAlmostEqual(added_score, 0, places=1, msg='added_score is wrong')

        # Test 1 day point difference - should be 2000 pts
        prev_post = {
            'total_score' : 0,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1',
            'time'        : datetime.datetime(2018, 7, 19, 22, 20, 25),
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
        added_score = self.bot.calculate_score_gained_curr_user(self.logger, prev_post, curr_post)
        self.assertAlmostEqual(added_score, 2000, places=5, msg='added_score is wrong')


    '''
    Tests deleted post detection
    '''
    def test_deleted_post_detection(self):
        # Should be detect as a deleted post since prev_post['time'] and curr_post['prev_post_time'] don't match
        prev_post = {
            'total_score' : 0,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1',
            'time'        : datetime.datetime(2018, 7, 19, 22, 20, 24),
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
        is_deleted_post = self.bot.is_deleted_post(self.logger, prev_post, curr_post)
        self.assertEqual(is_deleted_post, True, 'is_deleted_post is wrong')

        # Should not be detect as a deleted post since prev_post['time'] and curr_post['prev_post_time'] do match
        prev_post = {
            'total_score' : 0,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1',
            'time'        : datetime.datetime(2018, 7, 19, 22, 20, 23),
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
        is_deleted_post = self.bot.is_deleted_post(self.logger, prev_post, curr_post)
        self.assertEqual(is_deleted_post, False, 'is_deleted_post is wrong')

        # TODO: Test special events


    '''
    Tests previous user score calculation
    '''
    def test_prev_user_score_calc(self):
        # Test deleted post - score starts with 0 -> added_score should be 0
        prev_post = {
            'total_score' : 0,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1',
            'time'        : datetime.datetime(2018, 7, 19, 22, 20, 24),
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
        added_score = self.bot.calculate_score_gained_prev_user(self.logger, prev_post, curr_post)
        self.assertEqual(added_score, 0, 'added_score is wrong')

        # Test deleted post - score starts with 100 -> added_score should be -|100/2| = -50
        prev_post = {
            'total_score' : 100,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1',
            'time'        : datetime.datetime(2018, 7, 19, 22, 20, 24),
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
        added_score = self.bot.calculate_score_gained_prev_user(self.logger, prev_post, curr_post)
        self.assertEqual(added_score, -50, 'added_score is wrong')

        # Test deleted post - score starts with -100 -> added_score should be -|-100/2| = -50
        prev_post = {
            'total_score' : -100,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1',
            'time'        : datetime.datetime(2018, 7, 19, 22, 20, 24),
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
        added_score = self.bot.calculate_score_gained_prev_user(self.logger, prev_post, curr_post)
        self.assertEqual(added_score, -50, 'added_score is wrong')

        # Test deleted post - score starts with -2000000000 -> added_score should be -1
        prev_post = {
            'total_score' : -2000000000,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1',
            'time'        : datetime.datetime(2018, 7, 19, 22, 20, 24),
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
        added_score = self.bot.calculate_score_gained_prev_user(self.logger, prev_post, curr_post)
        self.assertEqual(added_score, -1, 'added_score is wrong')

        # Test deleted post - score starts with 2000000000 -> added_score should be -1000000000
        prev_post = {
            'total_score' : 2000000000,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1',
            'time'        : datetime.datetime(2018, 7, 19, 22, 20, 24),
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
        added_score = self.bot.calculate_score_gained_prev_user(self.logger, prev_post, curr_post)
        self.assertEqual(added_score, -1000000000, 'added_score is wrong')

        # Test normal post - score starts with x -> added_score should be 0
        prev_post = {
            'total_score' : 343434,
            'user_id'     : 1,
            'post_id'     : 123456,
            'user_name'   : 'test user 1',
            'time'        : datetime.datetime(2018, 7, 19, 22, 20, 23),
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
        added_score = self.bot.calculate_score_gained_prev_user(self.logger, prev_post, curr_post)
        self.assertEqual(added_score, 0, 'added_score is wrong')


    '''
    Tests top 10 list to return user points in the correct order and amount
    '''
    def test_top_10_all_time(self):
        # Add a bunch of random scores
        for i in range(11):
            data = {
                'added_score' : 100*random.random(),
                'user_id'     : i,
                'post_id'     : 10000 + i*10,
                'user_name'   : 'test user ' + str(i)
            }
            self.bot.update_user_data(self.logger, self.bot.get_db_table, data, DB_ENUM.ALL_TIME)

            top_10_list = self.bot.get_top_10_list(self.logger, self.bot.get_db_table, DB_ENUM.ALL_TIME)
            for i in range(len(top_10_list) - 1):
                self.assertGreaterEqual(top_10_list[i]['points'], top_10_list[i + 1]['points'], '#' + str(i) + ' pts are less than #' + str(i + 1))

        self.assertEqual(len(top_10_list), 10, 'Top 10 list does not have the expected number of entries')

        # Add a bunch of low scores
        for i in range(100):
            data = {
                'added_score' : 10*random.random(),
                'user_id'     : i,
                'post_id'     : 10000 + i*10,
                'user_name'   : 'test user ' + str(i)
            }
            self.bot.update_user_data(self.logger, self.bot.get_db_table, data, DB_ENUM.ALL_TIME)

            top_10_list = self.bot.get_top_10_list(self.logger, self.bot.get_db_table, DB_ENUM.ALL_TIME)
            for i in range(len(top_10_list) - 1):
                self.assertGreaterEqual(top_10_list[i]['points'], top_10_list[i + 1]['points'], '#' + str(i) + ' pts are less than #' + str(i + 1))

        self.assertEqual(len(top_10_list), 10, 'Top 10 list does not have the expected number of entries')

        # Add a bunch of high scores
        for i in range(100):
            data = {
                'added_score' : 1000*random.random(),
                'user_id'     : i,
                'post_id'     : 10000 + i*10,
                'user_name'   : 'test user ' + str(i)
            }
            self.bot.update_user_data(self.logger, self.bot.get_db_table, data, DB_ENUM.ALL_TIME)

            top_10_list = self.bot.get_top_10_list(self.logger, self.bot.get_db_table, DB_ENUM.ALL_TIME)
            for i in range(len(top_10_list) - 1):
                self.assertGreaterEqual(top_10_list[i]['points'], top_10_list[i + 1]['points'], '#' + str(i) + ' pts are less than #' + str(i + 1))

        self.assertEqual(len(top_10_list), 10, 'Top 10 list does not have the expected number of entries')


    '''
    Tests top scores list
    '''
    def test_top_scores_all_time(self):
        # Add a bunch of random scores
        for i in range(11):
            new_score_data = {
            'time'        : str(datetime.datetime(2018, 7, 19, 22, i, 25)),
            'user_id'     : str(i),
            'user_name'   : str('test user ' + str(i)),
            'post_id'     : str(10000 + i*10),
            'added_score' : '%.3f'%(100*random.random()),
            }
            self.bot.update_top_score_data(self.logger, self.bot.get_db_table, new_score_data, DB_ENUM.ALL_TIME)

            top_scores_list = self.bot.get_top_scores_list(self.logger, self.bot.get_db_table, DB_ENUM.ALL_TIME)
            for i in range(len(top_scores_list) - 1):
                self.assertGreaterEqual(float(top_scores_list[i]['added_score']), float(top_scores_list[i + 1]['added_score']), '#' + str(i) + ' pts are less than #' + str(i + 1))

        self.assertEqual(len(top_scores_list), 10, 'Top score list does not have the expected number of entries')

        # Add a bunch of low scores
        for i in range(100):
            new_score_data = {
                'time'        : str(datetime.datetime(2018, 7, 19, int(i/60)%24, i%60, 25)),
                'user_id'     : str(i),
                'user_name'   : str('test user ' + str(i)),
                'post_id'     : str(10000 + i*10),
                'added_score' : '%.3f'%(10*random.random()),
                }
            self.bot.update_top_score_data(self.logger, self.bot.get_db_table, new_score_data, DB_ENUM.ALL_TIME)

            top_scores_list = self.bot.get_top_scores_list(self.logger, self.bot.get_db_table, DB_ENUM.ALL_TIME)
            for i in range(len(top_scores_list) - 1):
                self.assertGreaterEqual(float(top_scores_list[i]['added_score']), float(top_scores_list[i + 1]['added_score']), '#' + str(i) + ' pts are less than #' + str(i + 1))

        self.assertEqual(len(top_scores_list), 10, 'Top score list does not have the expected number of entries')

        # Add a bunch of high scores
        for i in range(100):
            new_score_data = {
                'time'        : str(datetime.datetime(2018, 7, 19, int(i/60)%24, i%60, 25)),
                'user_id'     : str(i),
                'user_name'   : str('test user ' + str(i)),
                'post_id'     : str(10000 + i*10),
                'added_score' : '%.3f'%(1000*random.random()),
                }
            self.bot.update_top_score_data(self.logger, self.bot.get_db_table, new_score_data, DB_ENUM.ALL_TIME)

            top_scores_list = self.bot.get_top_scores_list(self.logger, self.bot.get_db_table, DB_ENUM.ALL_TIME)
            for i in range(len(top_scores_list) - 1):
                self.assertGreaterEqual(float(top_scores_list[i]['added_score']), float(top_scores_list[i + 1]['added_score']), '#' + str(i) + ' pts are less than #' + str(i + 1))

        self.assertEqual(len(top_scores_list), 10, 'Top score list does not have the expected number of entries')


    '''
    Tests log format?
    '''
    def test_top_scores_all_time(self):
        for i in range(11):
            user_score_all_time = self.bot.get_user_points(self.logger, self.bot.get_db_table, i, DB_ENUM.ALL_TIME)

            log_data = {
                'time'        : str(datetime.datetime(2018, 7, 19, 22, i, 25)),
                'user_name'   : str('test user ' + str(i)),
                'user_id'     : str(i),
                'post_id'     : str(10000 + i*10),
                'added_score' : '%.3f'%(100*random.random()),
                'total_score' : str(user_score_all_time)
            }
            self.bot.update_log_data(self.logger, self.bot.get_db_table, log_data, DB_ENUM.ALL_TIME)

        log_list = self.bot.get_log_list(self.logger, self.bot.get_db_table, DB_ENUM.ALL_TIME)
        # TODO: Testing


    '''
    Tests player's points after doing the add_user_points command
    '''
    def test_50__cmd_add_user_points__user_points(self):
        for i in range(100):
            data = {
                'added_score' : 100*random.random(),
                'user_id'     : i,
                'post_id'     : 10000 + i*10,
                'user_name'   : 'test user ' + str(i)
            }
            self.bot.update_user_data(self.logger, self.bot.get_db_table, data, DB_ENUM.ALL_TIME)

        # Test positive point addition to user
        test_user_50_pts_before = self.bot.get_user_points(self.logger, self.bot.get_db_table, 50, DB_ENUM.ALL_TIME)

        bot_cmd = ThreadNecroBotTest.BotCmd(self.logger, self.bot)
        print(bot_cmd.cmd_add_user_points['exec'](bot_cmd, 'test user 50', '123.456', 'all_time'))

        test_user_50_pts_after = self.bot.get_user_points(self.logger, self.bot.get_db_table, 50, DB_ENUM.ALL_TIME)

        # Make sure the correct number of points got added - should be a 123.456 difference
        diff = test_user_50_pts_after - test_user_50_pts_before
        self.assertEqual(round(diff, 3), 123.456, 'Score after does not match expected')

        # Test negative point addition to user
        test_user_50_pts_before = self.bot.get_user_points(self.logger, self.bot.get_db_table, 50, DB_ENUM.ALL_TIME)

        bot_cmd = ThreadNecroBotTest.BotCmd(self.logger, self.bot)
        print(bot_cmd.cmd_add_user_points['exec'](bot_cmd, 'test user 50', '-123.456', 'all_time'))

        test_user_50_pts_after = self.bot.get_user_points(self.logger, self.bot.get_db_table, 50, DB_ENUM.ALL_TIME)

        # Make sure the correct number of points got added - should be a -123.456 difference
        diff = test_user_50_pts_after - test_user_50_pts_before
        self.assertEqual(round(diff, 3), -123.456, 'Score after does not match expected')


    '''
    Tests the top 10 list after doing the add_user_points command
    '''
    def test_cmd_add_user_points__top_10_sort(self):
        for i in range(100):
            data = {
                'added_score' : 100*random.random(),
                'user_id'     : i,
                'post_id'     : 10000 + i*10,
                'user_name'   : 'test user ' + str(i)
            }
            self.bot.update_user_data(self.logger, self.bot.get_db_table, data, DB_ENUM.ALL_TIME)

        bot_cmd = ThreadNecroBotTest.BotCmd(self.logger, self.bot)
        print(bot_cmd.cmd_add_user_points['exec'](bot_cmd, 'test user 50', '1.23456', 'all_time'))

        # Make sure the top 10 list is returned sorted correctly after invoking the add_user_points command
        top_10_list = self.bot.get_top_10_list(self.logger, self.bot.get_db_table, DB_ENUM.ALL_TIME)
        for i in range(len(top_10_list) - 1):
            self.assertGreaterEqual(top_10_list[i]['points'], top_10_list[i + 1]['points'], '#' + str(i) + ' pts are less than #' + str(i + 1))

        self.assertEqual(len(top_10_list), 10, 'Top 10 list does not have the expected number of entries')
