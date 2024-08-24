from typing import Union

import math
import tinydb
import random
import datetime

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

from core.BotBase import BotBase
from core.BotException import BotException
from core.console_framework import Cmd

from core.parser import Topic, Post
from bots.ThreadNecroBotCore.ThreadNecroBotCore import ThreadNecroBotCore, DB_ENUM



class ThreadNecroBot(BotBase, ThreadNecroBotCore):

    DB_LOG_DATA  = 'LogData'
    DB_USER_DATA = 'UserData'

    def __init__(self, botcore):
        BotBase.__init__(self, botcore, self.BotCmd, self.__class__.__name__, enable=False)

        is_dbg = self.get_cfg('Core', 'is_dbg')

        self.subforum_id = '68'
        self.topic_id    = self.get_cfg('ThreadNecroBot', 'topic_id') if is_dbg else self.get_cfg('ThreadNecroBot', 'topic_id_test')
        self.main_post   = self.get_cfg('ThreadNecroBot', 'post_id')  if is_dbg else self.get_cfg('ThreadNecroBot', 'post_id_test')
        self.banned      = set()    # \TODO: this needs to go into db


    def post_init(self):
        ThreadNecroBotCore.__init__(self,
            db_tables = {
                DB_ENUM.ALL_TIME_LOG:    self.get_db_table('all_time_log'),
                DB_ENUM.ALL_TIME_SCORES: self.get_db_table('all_time_scores'),
                DB_ENUM.ALL_TIME_USER:   self.get_db_table('all_time_user'),

                DB_ENUM.MONTHLY_LOG:     self.get_db_table('monthly_log'),
                DB_ENUM.MONTHLY_SCORES:  self.get_db_table('monthly_scores'),
                DB_ENUM.MONTHLY_USER:    self.get_db_table('monthly_user'),
                DB_ENUM.MONTHLY_WINNERS: self.get_db_table('monthly_winners'),
            }
        )


    def filter_data(self, post: Post) -> bool:
        if post.topic.subforum_id != self.subforum_id:
            return False

        if post.topic.id != self.topic_id:
            return False

        if post.creator.id in self.banned:
            self.logger.info(f'Banned user posted; id: {post.creator.id}   username: {post.creator.name}')
            return False

        return True


    def process_data(self, post: Post):
        data = None

        if not post.prev_post:
            msg = f'Previous post does not exist; Current post id: {post.id}'
            raise BotException(self.logger, msg, show_traceback=False)

        # \TODO: Figure out how to ignore banned user's post entirely (not affect the game)
        data = {
            'curr_post_id'   : post.id,
            'prev_post_id'   : post.prev_post.id,
            'curr_post_time' : post.date,
            'prev_post_time' : post.prev_post.date,
            'curr_user_id'   : post.creator.id,
            'prev_user_id'   : post.prev_post.creator.id,
            'curr_user_name' : post.creator.name,
            'prev_user_name' : post.prev_post.creator.name
        }

        self.process_monthly_winner_event()
        prev_post_info = self.get_prev_post_info()

        self.process_prev_user(prev_post_info, data)  # This won't work unless it's in same forum
        self.process_curr_user(prev_post_info, data)
        #self.process_user_bonus(prev_post_info, data)

        self.write_post()


    def write_post(self):
        top_10_all_time_text     = self.get_top_10_text(self.get_top_10_list(DB_ENUM.DB_TYPE_ALL_TIME))
        top_scores_all_time_text = self.get_top_scores_text(self.get_top_scores_list(DB_ENUM.DB_TYPE_ALL_TIME))
        log_all_time_text        = self.get_forum_log_text(self.get_log_list(DB_ENUM.DB_TYPE_ALL_TIME))

        top_10_monthly_text     = self.get_top_10_text(self.get_top_10_list(DB_ENUM.DB_TYPE_MONTHLY))
        top_scores_monthly_text = self.get_top_scores_text(self.get_top_scores_list(DB_ENUM.DB_TYPE_MONTHLY))
        log_monthly_text        = self.get_forum_log_text(self.get_log_list(DB_ENUM.DB_TYPE_MONTHLY))

        monthly_winners_text    = self.get_monthly_winners_text(self.get_monthly_winners_list())

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
            '[box=Scoring formula][centre][img]https://i.imgur.com/HMPPxb1.png[/img][/centre][/box]\n'
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
        SessionMgr.edit_post(self.main_post, post_content, append=False)


    def calculate_score_gained_prev_user(self, prev_post_info: dict, data: dict):
        if not prev_post_info:
            return -1

        # Don't halve lower than this, no point
        if float(prev_post_info['total_score']) < -1000000000:
            return -1

        deleted_post = self.is_deleted_post(prev_post_info, data)
        halved_score = float(prev_post_info['total_score'])/2.0

        try:
            if deleted_post: added_score = -halved_score if (float(prev_post_info['total_score']) >= 0) else halved_score
            else:            added_score = 0
        except KeyError:     added_score = 0  # If prev_post_info is none (prev post doesn't exist yet)

        return added_score


    def calculate_score_gained_curr_user(self, prev_post_info: dict, data: dict):
        multi_post = self.is_multi_post(prev_post_info, data)

        if multi_post:
            added_score = -self.multi_post_pts_penalty
        else:
            seconds_passed = (data['curr_post_time'] - data['prev_post_time']).total_seconds()
            added_score    = self._b * math.pow(seconds_passed/60.0, self._n)

        return added_score


    def process_monthly_winner_event(self):
        current_date = datetime.datetime.now().replace(tzinfo=None)
        monthly_winners_list = self.get_monthly_winners_list()

        if not monthly_winners_list:
            starting_date = self.get_post(self.main_post).date.replace(tzinfo=None)
            next_date     = starting_date + relativedelta(months=1)

            current_delta = current_date - starting_date
            target_delta  = next_date - starting_date

            if current_delta >= target_delta:
                self.update_monthly_winners()
                self.reset_monthly_data()

                self.logger.info('Monthly winner recorded; New Monthly Chart made!')

        else:
            previous_date = parse(monthly_winners_list[-1]['time']).replace(tzinfo=None)
            next_date     = previous_date + relativedelta(months=1)

            current_delta = current_date - previous_date
            target_delta  = next_date - previous_date

            if current_delta >= target_delta:
                self.update_monthly_winners()
                self.reset_monthly_data()

                self.logger.info('Monthly winner recorded; New Monthly Chart made!')


    def process_prev_user(self, prev_post_info: dict, data: dict):
        # If prev_post_info is none (prev post doesn't exist yet)
        if not prev_post_info:
            return

        is_multi_post   = self.is_multi_post(prev_post_info, data)
        is_deleted_post = self.is_deleted_post(prev_post_info, data)

        added_score = self.calculate_score_gained_prev_user(prev_post_info, data)
        if added_score == 0:
            return

        try:
            user_data = {
                'added_score' : added_score,
                'user_id'     : prev_post_info['user_id'],
                'user_name'   : prev_post_info['user_name'],
                'post_id'     : prev_post_info['post_id']
            }

            self.update_user_data(user_data, DB_ENUM.DB_TYPE_ALL_TIME)
            self.update_user_data(user_data, DB_ENUM.DB_TYPE_MONTHLY)

            user_score_all_time = self.get_user_points(prev_post_info['user_id'], DB_ENUM.DB_TYPE_ALL_TIME)
            user_score_monthly  = self.get_user_points(prev_post_info['user_id'], DB_ENUM.DB_TYPE_MONTHLY)

            if is_multi_post:   log_timestamp = self.get_timestamp(ThreadNecroBotCore.MULTI_TIMESTAMP)
            if is_deleted_post: log_timestamp = self.get_timestamp(ThreadNecroBotCore.DELET_TIMESTAMP)

            log_data = {
                'time'        : f'{log_timestamp}',
                'user_name'   : f'{prev_post_info["user_name"]}',
                'user_id'     : f'{prev_post_info["user_id"]}',
                'post_id'     : f'{prev_post_info["post_id"]}',
                'added_score' : f'{added_score:.3f}',
                'total_score' : f'{user_score_all_time}'
            }
            self.update_log_data(log_data, DB_ENUM.DB_TYPE_ALL_TIME)

            log_data = {
                'time'        : f'{log_timestamp}',
                'user_name'   : f'{prev_post_info["user_name"]}',
                'user_id'     : f'{prev_post_info["user_id"]}',
                'post_id'     : f'{prev_post_info["post_id"]}',
                'added_score' : f'{added_score:.3f}',
                'total_score' : f'{user_score_monthly}',
            }
            self.update_log_data(log_data, DB_ENUM.DB_TYPE_MONTHLY)

        except KeyError as e:
            self.logger.error(str(e))
            return


    def process_curr_user(self, prev_post_info: dict, data: dict):
        added_score = self.calculate_score_gained_curr_user(prev_post_info, data)

        user_data = {
            'added_score' : added_score,
            'user_id'     : data['curr_user_id'],
            'user_name'   : data['curr_user_name'],
            'post_id'     : data['curr_post_id']
        }

        self.update_user_data(user_data, DB_ENUM.DB_TYPE_ALL_TIME)
        self.update_user_data(user_data, DB_ENUM.DB_TYPE_MONTHLY)

        user_score_all_time = self.get_user_points(data['curr_user_id'], DB_ENUM.DB_TYPE_ALL_TIME)
        user_score_monthly  = self.get_user_points(data['curr_user_id'], DB_ENUM.DB_TYPE_MONTHLY)

        log_data = {
            'time'        : str(data['curr_post_time']),
            'user_name'   : str(data['curr_user_name']),
            'user_id'     : str(data['curr_user_id']),
            'post_id'     : str(data['curr_post_id']),
            'added_score' : str('%.3f'%(added_score)),
            'total_score' : str(user_score_all_time)
        }
        self.update_log_data(log_data, DB_ENUM.DB_TYPE_ALL_TIME)

        log_data = {
            'time'        : str(data['curr_post_time']),
            'user_name'   : str(data['curr_user_name']),
            'user_id'     : str(data['curr_user_id']),
            'post_id'     : str(data['curr_post_id']),
            'added_score' : str('%.3f'%(added_score)),
            'total_score' : str(user_score_monthly)
        }
        self.update_log_data(log_data, DB_ENUM.DB_TYPE_MONTHLY)

        new_score_data = {
            'time'        : str(data['curr_post_time']),
            'user_id'     : str(data['curr_user_id']),
            'user_name'   : str(data['curr_user_name']),
            'post_id'     : str(data['curr_post_id']),
            'added_score' : '%.3f'%(added_score),
        }
        self.update_top_score_data(new_score_data, DB_ENUM.DB_TYPE_ALL_TIME)
        self.update_top_score_data(new_score_data, DB_ENUM.DB_TYPE_MONTHLY)


    def process_user_bonus(self, prev_post_info: dict, data: dict):
        rank = self.get_user_rank(str(data['curr_user_id']), DB_ENUM.DB_TYPE_ALL_TIME)
        if not rank: return

        number = random.randint(1, pow(2, rank))
        if number != 1: return

        added_score = float(self.get_top_scores_list(DB_ENUM.DB_TYPE_ALL_TIME)[-1]['added_score'])

        user_data = {
            'added_score' : added_score,
            'user_id'     : data['curr_user_id'],
            'user_name'   : data['curr_user_name'],
            'post_id'     : data['curr_post_id']
        }

        self.update_user_data(user_data, DB_ENUM.DB_TYPE_ALL_TIME)
        self.update_user_data(user_data, DB_ENUM.DB_TYPE_MONTHLY)

        user_score_all_time = self.get_user_points(data['curr_user_id'], DB_ENUM.DB_TYPE_ALL_TIME)
        user_score_monthly  = self.get_user_points(data['curr_user_id'], DB_ENUM.DB_TYPE_MONTHLY)

        log_data = {
            'time'        : str(self.get_timestamp(ThreadNecroBotCore.BONUS_TIMESTAMP)),
            'user_name'   : str(data['curr_user_name']),
            'user_id'     : str(data['curr_user_id']),
            'post_id'     : str(data['curr_post_id']),
            'added_score' : str('%.3f'%(added_score)),
            'total_score' : str(user_score_all_time)
        }
        self.update_log_data(log_data, DB_ENUM.DB_TYPE_ALL_TIME)

        log_data = {
            'time'        : str(self.get_timestamp(ThreadNecroBotCore.BONUS_TIMESTAMP)),
            'user_name'   : str(data['curr_user_name']),
            'user_id'     : str(data['curr_user_id']),
            'post_id'     : str(data['curr_post_id']),
            'added_score' : str('%.3f'%(added_score)),
            'total_score' : str(user_score_monthly)
        }
        self.update_log_data(log_data, DB_ENUM.DB_TYPE_MONTHLY)


    class BotCmd(Cmd):

        def __init__(self, logger, obj: "ThreadNecroBot"):
            self.logger = logger
            self.obj    = obj


        def get_bot_moderators(self):
            return []


        def validate_special_perm(self, requestor_id, access_id):
            return False


        @Cmd.help(
        perm = Cmd.PERMISSION_PUBLIC,
        info = 'Prints the about text for ThreadNecroBot',
        args = {
        })
        def cmd_about(self):
            return Cmd.ok(
                'ThreadNecroBot runs the Thread Necromancy game in forum game subforum in osu! forums\n'
                '\n'
                'The awards points based on how long it has been since the last post was made. The more time passed, the more points. If a post gets deleted, the user\'s points halved.'
            )


        @Cmd.help(
        perm = Cmd.PERMISSION_PUBLIC,
        info = 'Prints the help text for ThreadNecroBot',
        args = {
        })
        def cmd_help(self):
            return Cmd.ok('To be implemented...')


        @Cmd.help(
        perm = Cmd.PERMISSION_PUBLIC,
        info = 'Prints the number of points the specified user has',
        args = {
            'user_name' : Cmd.arg(str, False, 'Name of the user to print the number of point of'),
            'db_type'   : Cmd.arg(str, False, 'all_time or monthly')
        })
        def cmd_get_user_points(self, user_name: str, db_type: str):
            if   db_type == 'all_time': user_data_table = self.obj.db_tables[DB_ENUM.ALL_TIME_USER]
            elif db_type == 'monthly':  user_data_table = self.obj.db_tables[DB_ENUM.MONTHLY_USER]
            else: return Cmd.err('Invalid db type specified. Use "all_time" or "monthly"')

            # Request
            query = tinydb.Query()
            entry = user_data_table.get(query.user_name == str(user_name))

            # Process
            if not entry:
                return Cmd.err(f'Unable to find user "{user_name}"')

            return Cmd.ok(f'{user_name} has {entry["points"]} pts')


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Adds the specified number of points to the user specified or subtracts if the value is negative',
        args = {
            'user_name' : Cmd.arg(str,   False, 'Name of the user to add or take points from'),
            'points'    : Cmd.arg(float, False, 'Number of points to add'),
            'db_type'   : Cmd.arg(str,   False, 'all_time or monthly')
        })
        def cmd_add_user_points(self, cmd_key, user_name, points, db_type):
            """
            db Format:
            {
                user_id : { 'points' : '...', 'user_name' : '...', 'post_id' : '...' },
                user_id : { 'points' : '...', 'user_name' : '...', 'post_id' : '...' },
                ...
            }
            """
            if not self.validate_request(cmd_key):
                return Cmd.err('Insufficient permissions')

            if   db_type == 'all_time': db_type = DB_ENUM.DB_TYPE_ALL_TIME; user_data_table = self.obj.db_tables[DB_ENUM.ALL_TIME_USER]
            elif db_type == 'monthly':  db_type = DB_ENUM.DB_TYPE_MONTHLY;  user_data_table = self.obj.db_tables[DB_ENUM.MONTHLY_USER]
            else:
                return Cmd.err('Invalid db type specified. Use "all_time" or "monthly"')

            # Request
            query = tinydb.Query()
            entry = user_data_table.get(query.user_name == str(user_name))

            # Process
            if not entry:
                return Cmd.err(f'Unable to find user "{user_name}"')

            new_points = float(entry['points']) + float(points)
            user_id    = entry.doc_id

            # Update
            entry['points'] = new_points
            user_data_table.update(entry, doc_ids=[ entry.doc_id ])

            log_data = {
                'time'        : str(self.obj.get_timestamp(ThreadNecroBotCore.ADMIN_TIMESTAMP)),
                'user_name'   : str(user_name),
                'user_id'     : str(user_id),
                'post_id'     : str(),
                'added_score' : str('%.3f'%(float(points))),
                'total_score' : str('%.3f'%(float(new_points)))
            }
            self.obj.update_log_data(log_data, db_type)

            try: self.obj.write_post()
            except:
                pass

            return Cmd.ok(f'{user_name} now has {new_points} pts - {db_type}')


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Gets the info of the previous post recorded',
        args = {
        })
        def cmd_get_prev_post_info(self, cmd_key):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            return Cmd.ok(str(self.obj.get_prev_post_info(self.obj.get_db_table)))


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Bans the user with the given user id from the game',
        args = {
            'user_id' : Cmd.arg(int, False, 'User id')
        })
        def cmd_ban(self, cmd_key, user_id):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            return Cmd.err('TODO')
            '''
            if user_id not in self.obj.banned:
                # TODO: Wipe user from db
                self.obj.banned.add(user_id)
                return { 'status' : 0, 'msg' : 'banned player' }

            return { 'status' : 0, 'msg' : 'user is already banned' }
            '''


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Unbans the user with the given user id from the game',
        args = {
        })
        def cmd_unban(self, cmd_key, user_id):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            return Cmd.err('TODO')
            '''
            if user_id in self.obj.banned:
                self.obj.banned.remove(user_id)
                return 'Unbanned player'

            return 'user not banned'
            '''


        @Cmd.help(
        perm = Cmd.PERMISSION_PUBLIC,
        info = 'Retrieves the user\'s rank based on the specified user ID',
        args = {
            'user_id' : Cmd.arg(int, False, 'User id')
        })
        def cmd_get_user_rank(self, user_id):
            rank = self.obj.get_user_rank(user_id)
            if not rank:
                return Cmd.err('user not found')

            return Cmd.ok(f'User is ranked {rank}')


        @Cmd.help(
        perm = Cmd.PERMISSION_PUBLIC,
        info = 'Prints a list of user_ids who are banned from the game',
        args = {
            'user_id' : Cmd.arg(int, False, 'User id')
        })
        def cmd_get_banned(self, user_id):
            return Cmd.ok(str(self.obj.banned))
