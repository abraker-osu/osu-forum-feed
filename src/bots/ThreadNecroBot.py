from typing import Union

import math
import tinydb
import random
import datetime

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

from core.botcore.BotBase import BotBase
from core.botcore.BotException import BotException
from core.botcore.console_framework.Cmd import Cmd

from core.parser import Topic, Post
from core.SessionMgr import SessionMgr

from bots.ThreadNecroBotCore.ThreadNecroBotCore import ThreadNecroBotCore, DB_ENUM



class ThreadNecroBot(BotBase, ThreadNecroBotCore):

    DB_LOG_DATA  = 'LogData'
    DB_USER_DATA = 'UserData'

    def __init__(self, botcore):
        BotBase.__init__(self, botcore, self.BotCmd, self.__class__.__name__, enable=False)

        self.subforum_id = '68'
        self.thread_id   = '802725'
        self.main_post   = '6804359'
        self.banned      = set()    # \TODO: this needs to go into db


    def post_init(self):
        ThreadNecroBotCore.__init__(self)


    def filter_data(self, forum_data: Union[Post, Topic]) -> bool:
        if not isinstance(forum_data, Post):
            return False

        if forum_data.topic.subforum_id != self.subforum_id:
            return False

        if forum_data.topic.id != self.thread_id:
            return False

        if forum_data.creator.id in self.banned:
            self.logger.info(f'Banned user posted; id: {forum_data.creator.id}   username: {forum_data.creator.name}')
            return False

        return True


    def process_data(self, post: Post):
        data = None

        if not post.prev_post:
            msg = 'Previous post does not exist; Current post id: {post.id}'
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
        db = self.get_db(__class__.__name__)

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


    def calculate_score_gained_prev_user(self, prev_post_info, data):
        if not prev_post_info: return -1

        # Don't halve lower than this, no point
        if float(prev_post_info['total_score']) < -1000000000:
            return -1

        deleted_post = self.is_deleted_post(self.logger, prev_post_info, data)
        halved_score = float(prev_post_info['total_score'])/2.0

        try:
            if deleted_post: added_score = -halved_score if (float(prev_post_info['total_score']) >= 0) else halved_score
            else:            added_score = 0
        except KeyError:     added_score = 0  # If prev_post_info is none (prev post doesn't exist yet)

        return added_score


    def calculate_score_gained_curr_user(self, prev_post_info, data):
        multi_post = self.is_multi_post(self.logger, prev_post_info, data)

        if multi_post:
            added_score = -self.multi_post_pts_penalty
        else:
            seconds_passed = (data['curr_post_time'] - data['prev_post_time']).total_seconds()
            added_score    = self._b * math.pow(seconds_passed/60.0, self._n)

        return added_score


    def process_monthly_winner_event(self, db):
        current_date = datetime.datetime.now().replace(tzinfo=None)
        monthly_winners_list = self.get_monthly_winners_list(self.logger, db)

        if not monthly_winners_list:
            starting_date = self.get_post(self.main_post).date.replace(tzinfo=None)
            next_date     = starting_date + relativedelta(months=1)

            current_delta = current_date - starting_date
            target_delta  = next_date - starting_date

            if current_delta >= target_delta:
                self.update_monthly_winners(self.logger, db)
                self.reset_monthly_data(self.logger, db)

                self.logger.info('Monthly winner recorded; New Monthly Chart made!')

        else:
            previous_date = parse(monthly_winners_list[-1]['time']).replace(tzinfo=None)
            next_date     = previous_date + relativedelta(months=1)

            current_delta = current_date - previous_date
            target_delta  = next_date - previous_date

            if current_delta >= target_delta:
                self.update_monthly_winners(self.logger, db)
                self.reset_monthly_data(self.logger, db)

                self.logger.info('Monthly winner recorded; New Monthly Chart made!')


    def process_prev_user(self, db, prev_post_info, data):
        # If prev_post_info is none (prev post doesn't exist yet)
        if not prev_post_info:
            return

        is_multi_post = self.is_multi_post(self.logger, prev_post_info, data)
        is_deleted_post = self.is_deleted_post(self.logger, prev_post_info, data)

        added_score = self.calculate_score_gained_prev_user(self.logger, prev_post_info, data)
        if added_score == 0:
            return

        try:
            user_data = {
                'added_score' : added_score,
                'user_id'     : prev_post_info['user_id'],
                'user_name'   : prev_post_info['user_name'],
                'post_id'     : prev_post_info['post_id']
            }

            self.update_user_data(self.logger, db, user_data, DB_ENUM.ALL_TIME)
            self.update_user_data(self.logger, db, user_data, DB_ENUM.MONTHLY)

            user_score_all_time = self.get_user_points(self.logger, db, prev_post_info['user_id'], DB_ENUM.ALL_TIME)
            user_score_monthly  = self.get_user_points(self.logger, db, prev_post_info['user_id'], DB_ENUM.MONTHLY)

            if is_multi_post:   log_timestamp = self.get_timestamp(ThreadNecroBotCore.MULTI_TIMESTAMP)
            if is_deleted_post: log_timestamp = self.get_timestamp(ThreadNecroBotCore.DELET_TIMESTAMP)

            log_data = {
                'time'        : str(log_timestamp),
                'user_name'   : str(prev_post_info['user_name']),
                'user_id'     : str(prev_post_info['user_id']),
                'post_id'     : str(prev_post_info['post_id']),
                'added_score' : str('%.3f'%(added_score)),
                'total_score' : str(user_score_all_time)
            }
            self.update_log_data(self.logger, db, log_data, DB_ENUM.ALL_TIME)

            log_data = {
                'time'        : str(log_timestamp),
                'user_name'   : str(prev_post_info['user_name']),
                'user_id'     : str(prev_post_info['user_id']),
                'post_id'     : str(prev_post_info['post_id']),
                'added_score' : str('%.3f'%(added_score)),
                'total_score' : str(user_score_monthly)
            }
            self.update_log_data(self.logger, db, log_data, DB_ENUM.MONTHLY)

        except KeyError as e:
            self.logger.error(str(e))
            return


    def process_curr_user(self, db, prev_post_info, data):
        added_score = self.calculate_score_gained_curr_user(self.logger, prev_post_info, data)

        user_data = {
            'added_score' : added_score,
            'user_id'     : data['curr_user_id'],
            'user_name'   : data['curr_user_name'],
            'post_id'     : data['curr_post_id']
        }

        self.update_user_data(self.logger, db, user_data, DB_ENUM.ALL_TIME)
        self.update_user_data(self.logger, db, user_data, DB_ENUM.MONTHLY)

        user_score_all_time = self.get_user_points(self.logger, db, data['curr_user_id'], DB_ENUM.ALL_TIME)
        user_score_monthly  = self.get_user_points(self.logger, db, data['curr_user_id'], DB_ENUM.MONTHLY)

        log_data = {
            'time'        : str(data['curr_post_time']),
            'user_name'   : str(data['curr_user_name']),
            'user_id'     : str(data['curr_user_id']),
            'post_id'     : str(data['curr_post_id']),
            'added_score' : str('%.3f'%(added_score)),
            'total_score' : str(user_score_all_time)
        }
        self.update_log_data(self.logger, db, log_data, DB_ENUM.ALL_TIME)

        log_data = {
            'time'        : str(data['curr_post_time']),
            'user_name'   : str(data['curr_user_name']),
            'user_id'     : str(data['curr_user_id']),
            'post_id'     : str(data['curr_post_id']),
            'added_score' : str('%.3f'%(added_score)),
            'total_score' : str(user_score_monthly)
        }
        self.update_log_data(self.logger, db, log_data, DB_ENUM.MONTHLY)

        new_score_data = {
            'time'        : str(data['curr_post_time']),
            'user_id'     : str(data['curr_user_id']),
            'user_name'   : str(data['curr_user_name']),
            'post_id'     : str(data['curr_post_id']),
            'added_score' : '%.3f'%(added_score),
        }
        self.update_top_score_data(self.logger, db, new_score_data, DB_ENUM.ALL_TIME)
        self.update_top_score_data(self.logger, db, new_score_data, DB_ENUM.MONTHLY)


    def process_user_bonus(self, db, prev_post_info, data):
        rank = self.get_user_rank(self.logger, db, str(data['curr_user_id']), DB_ENUM.ALL_TIME)
        if not rank: return

        number = random.randint(1, pow(2, rank))
        if number != 1: return

        added_score = float(self.get_top_scores_list(self.logger, db, DB_ENUM.ALL_TIME)[-1]['added_score'])

        user_data = {
            'added_score' : added_score,
            'user_id'     : data['curr_user_id'],
            'user_name'   : data['curr_user_name'],
            'post_id'     : data['curr_post_id']
        }

        self.update_user_data(self.logger, db, user_data, DB_ENUM.ALL_TIME)
        self.update_user_data(self.logger, db, user_data, DB_ENUM.MONTHLY)

        user_score_all_time = self.get_user_points(self.logger, db, data['curr_user_id'], DB_ENUM.ALL_TIME)
        user_score_monthly  = self.get_user_points(self.logger, db, data['curr_user_id'], DB_ENUM.MONTHLY)

        log_data = {
            'time'        : str(self.get_timestamp(ThreadNecroBotCore.BONUS_TIMESTAMP)),
            'user_name'   : str(data['curr_user_name']),
            'user_id'     : str(data['curr_user_id']),
            'post_id'     : str(data['curr_post_id']),
            'added_score' : str('%.3f'%(added_score)),
            'total_score' : str(user_score_all_time)
        }
        self.update_log_data(self.logger, db, log_data, DB_ENUM.ALL_TIME)

        log_data = {
            'time'        : str(self.get_timestamp(ThreadNecroBotCore.BONUS_TIMESTAMP)),
            'user_name'   : str(data['curr_user_name']),
            'user_id'     : str(data['curr_user_id']),
            'post_id'     : str(data['curr_post_id']),
            'added_score' : str('%.3f'%(added_score)),
            'total_score' : str(user_score_monthly)
        }
        self.update_log_data(self.logger, db, log_data, DB_ENUM.MONTHLY)


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
        def cmd_get_user_points(self, user_name, db_type):
            if   db_type == 'all_time': db_type = DB_ENUM.ALL_TIME
            elif db_type == 'monthly':  db_type = DB_ENUM.MONTHLY
            else: return Cmd.err('Invalid db type specified. Use "all_time" or "monthly"')

            user_data_collection = self.obj.get_db_table(self.obj.get_db(db_type, DB_ENUM.USER_DATA))

            # Request
            query      = { 'user_name' : str(user_name) }
            projection = { 'points' : 1 }
            cursor = user_data_collection.find_one(query, projection=projection)

            # Process
            if cursor:  response = str(user_name) + ' has ' + str(cursor['points']) + ' pts'
            else:       return Cmd.err('Unable to find user "' + user_name + '"')

            if cursor: del cursor
            return Cmd.ok(response)


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Adds the specified number of points to the user specified or subtracts if the value is negative',
        args = {
            'user_name' : Cmd.arg(str,   False, 'Name of the user to add or take points from'),
            'points'    : Cmd.arg(float, False, 'Number of points to add'),
            'db_type'   : Cmd.arg(str,   False, 'all_time or monthly')
        })
        def cmd_add_user_points(self, cmd_key, user_name, points, db_type):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            if   db_type == 'all_time': db_type = DB_ENUM.ALL_TIME
            elif db_type == 'monthly':  db_type = DB_ENUM.MONTHLY
            else: return Cmd.err('Invalid db type specified. Use "all_time" or "monthly"')

            user_data_collection = self.obj.get_db_table(self.obj.get_db(db_type, DB_ENUM.USER_DATA))

            # Request
            query      = { 'user_name' : str(user_name) }
            projection = { 'points' : 1, 'user_id' : 1 }

            cursor = user_data_collection.find_one(query, projection=projection)
            if not cursor: return Cmd.err('Unable to find user "' + user_name + '"')

            # Process
            new_points = float(cursor['points']) + float(points)
            user_id    = cursor['user_id']
            if cursor: del cursor

            # Update
            query = { 'user_id' : str(user_id) }
            value = { 'points'  : float(new_points) }
            user_data_collection.update_one(query, { "$set" : value }, upsert=True)

            log_data = {
                'time'        : str(self.obj.get_timestamp(ThreadNecroBotCore.ADMIN_TIMESTAMP)),
                'user_name'   : str(user_name),
                'user_id'     : str(user_id),
                'post_id'     : str(),
                'added_score' : str('%.3f'%(float(points))),
                'total_score' : str('%.3f'%(float(new_points)))
            }
            self.obj.update_log_data(self.obj._logger, self.obj.get_db_table, log_data, db_type)

            try: self.obj.write_post(self.obj._logger, self.obj.get_db_table)
            except: pass

            return Cmd.ok(f'{user_name} now has {new_points} pts - {db_type}')


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Gets the info of the previous post recorded',
        args = {
        })
        def cmd_get_prev_post_info(self, cmd_key):
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            return Cmd.ok(str(self.obj.get_prev_post_info(self.logger, self.obj.get_db_table)))


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
                # \TODO: Wipe user from db
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
            rank = self.obj.get_user_rank(self.logger, self.obj.get_db_table, user_id)
            if not rank: return Cmd.err('user not found')

            return Cmd.err(f'User is ranked {rank}')


        @Cmd.help(
        perm = Cmd.PERMISSION_PUBLIC,
        info = 'Prints a list of user_ids who are banned from the game',
        args = {
            'user_id' : Cmd.arg(int, False, 'User id')
        })
        def cmd_get_banned(self, user_id):
            return Cmd.ok(str(self.obj.banned))
