import math
import random
import datetime

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

from core.BotConfig import BotConfig
from core.BotBase import BotBase
from core.BotException import BotException
from core.SessionMgrV2 import SessionMgrV2
from core.parser.Post import Post

from api.Cmd import Cmd

from .ThreadNecroBotCore.ThreadNecroBotCore import ThreadNecroBotCore


class ThreadNecroBot(BotBase, ThreadNecroBotCore):

    __MULTI_POST_PTS_PENALTY = -100

    __SUBFORUM_ID = 68

    def __init__(self):
        BotBase.__init__(self, self.BotCmd, self.__class__.__name__, enable=True)

        is_dbg = BotConfig['Core']['is_dbg']

        self.topic_id  = BotConfig['ThreadNecroBot']['topic_id_dbg'] if is_dbg else BotConfig['ThreadNecroBot']['topic_id']
        self.main_post = BotConfig['ThreadNecroBot']['post_id_dbg']  if is_dbg else BotConfig['ThreadNecroBot']['post_id']
        self.banned    = set()    # \TODO: this needs to go into db


    def post_init(self):
        is_dbg  = BotConfig['Core']['is_dbg']
        db_path = BotConfig['Core']['db_path_dbg'] if is_dbg else BotConfig['Core']['db_path']
        ThreadNecroBotCore.__init__(self, db_path)


    def filter_data(self, post: Post) -> bool:
        if post.topic.subforum_id != self.__SUBFORUM_ID:
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

        # Prev user must be processes before current user
        # Also prev user processing won't work unless it's the same thread
        self.process_prev_user(data)
        self.process_curr_user(data)
        #self.process_user_bonus(data)

        self.write_post()


    def write_post(self):
        top_10_all_time_text     = self.get_top_10_text(self.DB_TYPE_ALLTIME)
        top_scores_all_time_text = self.get_top_scores_text(self.DB_TYPE_ALLTIME)
        log_all_time_text        = self.get_forum_log_text(self.DB_TYPE_ALLTIME)

        top_10_monthly_text      = self.get_top_10_text(self.DB_TYPE_MONTHLY)
        top_scores_monthly_text  = self.get_top_scores_text(self.DB_TYPE_MONTHLY)
        log_monthly_text         = self.get_forum_log_text(self.DB_TYPE_MONTHLY)

        monthly_winners_text     = self.get_monthly_winners_text()

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
            '[box=Scoring formula][centre][img]https://abraker.s-ul.eu/12svGcIl[/img][/centre][/box]\n'
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
        SessionMgrV2.edit_post(self.main_post, post_content, append=False)


    def calculate_score_gained_prev_user(self, prev_post_info: dict, data: dict):
        """
        fmt `prev_post_info`:
            { 'prev_post_id' : int, 'prev_post_time' : str, 'prev_post_user_id' : int }

        fmt `data`:
            {
                'curr_post_id'   : int,
                'prev_post_id'   : int,
                'curr_post_time' : int,
                'prev_post_time' : int,
                'curr_user_id'   : int,
                'prev_user_id'   : int,
                'curr_user_name' : str,
                'prev_user_name' : str
            }
        """
        if not prev_post_info:
            return -1

        score = self.get_user_points(prev_post_info['prev_post_user_id'], self.DB_TYPE_MONTHLY)

        # Don't halve lower than this, no point
        if score < -1000000000:
            return -1

        deleted_post = self.is_deleted_post(prev_post_info, data)
        halved_score = score/2.0

        try:
            if deleted_post: return -halved_score if (score >= 0) else halved_score
            else:            return 0
        except KeyError:
            # If prev_post_info is none (prev post doesn't exist yet)
            return 0


    def calculate_score_gained_curr_user(self, prev_post_info: dict, data: dict):
        """
        fmt `prev_post_info`:
            { 'prev_post_id' : int, 'prev_post_time' : str, 'prev_post_user_id' : int }

        fmt `data`:
            {
                'curr_post_id'   : int,
                'prev_post_id'   : int,
                'curr_post_time' : int,
                'prev_post_time' : int,
                'curr_user_id'   : int,
                'prev_user_id'   : int,
                'curr_user_name' : str,
                'prev_user_name' : str
            }
        """
        if self.is_multi_post(prev_post_info, data):
            return self.__MULTI_POST_PTS_PENALTY

        curr_post_time = data['curr_post_time']
        if isinstance(curr_post_time, str):
            curr_post_time = datetime.datetime.fromisoformat(curr_post_time)

        prev_post_time = prev_post_info['prev_post_time']
        if isinstance(prev_post_time, str):
            prev_post_time = datetime.datetime.fromisoformat(prev_post_time)

        seconds_passed = (curr_post_time - prev_post_time).total_seconds()
        return self._b * math.pow(seconds_passed/60.0, self._n)


    def process_monthly_winner_event(self):
        current_date = datetime.datetime.now().replace(tzinfo=None)
        monthly_winners_list = self.get_monthly_winners_list()

        if not monthly_winners_list:
            starting_date = SessionMgrV2.get_post(self.main_post).date.replace(tzinfo=None)
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


    def process_prev_user(self, data: dict):
        """
        fmt `data`:
        {
            'curr_post_id'   : int,
            'prev_post_id'   : int,
            'curr_post_time' : int,
            'prev_post_time' : int,
            'curr_user_id'   : int,
            'prev_user_id'   : int,
            'curr_user_name' : str,
            'prev_user_name' : str
        }
        """
        # If prev_post_info is none (prev post doesn't exist yet)
        prev_post_info = self.get_prev_post_info()
        if not prev_post_info:
            return

        added_score = self.calculate_score_gained_prev_user(prev_post_info, data)
        if added_score == 0:
            return

        log_timestamp = None
        if self.is_multi_post(prev_post_info, data):
            log_timestamp = ThreadNecroBotCore.LOG_TIMESTAMP_MULTI
        elif self.is_deleted_post(prev_post_info, data):
            log_timestamp = ThreadNecroBotCore.LOG_TIMESTAMP_DELET

        data = {
            'time'        : str(f'{log_timestamp}'),
            'user_id'     : int(prev_post_info['user_id']),
            'user_name'   : str(prev_post_info['user_name']),
            'post_id'     : int(prev_post_info['post_id']),
            'added_score' : float(f'{added_score:.3f}')
        }

        self.update_user_data(data)

        if log_timestamp:
            self.update_log_data(data)
            self.logger.info(self.generate_log_line(data))


    def process_curr_user(self, data: dict):
        """
        fmt `data`:
            {
                'curr_post_id'   : int,
                'prev_post_id'   : int,
                'curr_post_time' : int,
                'prev_post_time' : int,
                'curr_user_id'   : int,
                'prev_user_id'   : int,
                'curr_user_name' : str,
                'prev_user_name' : str
            }
        """
        # If prev_post_info is none (prev post doesn't exist yet)
        prev_post_info = self.get_prev_post_info()
        if not prev_post_info:
            prev_post_info = {
                'prev_post_id'      : data['prev_post_id'],
                'prev_post_time'    : data['prev_post_time'],
                'prev_post_user_id' : data['prev_user_id']
            }

        added_score = self.calculate_score_gained_curr_user(prev_post_info, data)
        data = {
            'time'        : str(data['curr_post_time']),
            'user_name'   : str(data['curr_user_name']),
            'user_id'     : str(data['curr_user_id']),
            'post_id'     : str(data['curr_post_id']),
            'added_score' : str('%.3f'%(added_score)),
        }

        self.update_user_data(data)
        self.update_log_data(data)
        self.update_top_score_data(data)
        self.update_metadata(data)

        self.logger.info(self.generate_log_line(data))


    def process_user_bonus(self, data: dict):
        """
        fmt `data`:
            {
                'curr_post_id'   : int,
                'prev_post_id'   : int,
                'curr_post_time' : int,
                'prev_post_time' : int,
                'curr_user_id'   : int,
                'prev_user_id'   : int,
                'curr_user_name' : str,
                'prev_user_name' : str
            }
        """
        rank = self.get_user_rank(str(data['curr_user_id']), self.DB_TYPE_ALLTIME)
        if not rank:
            return

        number = random.randint(1, pow(2, rank))
        if number != 1:
            return

        added_score = float(self.get_top_scores_list(self.DB_TYPE_ALLTIME)[-1]['added_score'])
        data = {
            'time'        : str(ThreadNecroBotCore.LOG_TIMESTAMP_BONUS),
            'user_id'     : int(data['curr_user_id']),
            'user_name'   : str(data['curr_user_name']),
            'post_id'     : int(data['curr_post_id']),
            'added_score' : float(f'{added_score:.3f}'),
        }

        self.update_user_data(data)
        self.update_log_data(data)

        self.logger.info(self.generate_log_line(data))


    def is_multi_post(self, prev_post_info: dict, data: dict):
        """
        fmt `prev_post_info`:
            { 'prev_post_id' : int, 'prev_post_time' : str, 'prev_post_user_id' : int }

        fmt `data`:
            {
                'curr_post_id'   : int,
                'prev_post_id'   : int,
                'curr_post_time' : int,
                'prev_post_time' : int,
                'curr_user_id'   : int,
                'prev_user_id'   : int,
                'curr_user_name' : str,
                'prev_user_name' : str
            }
        """
        try: return ( int(prev_post_info['prev_post_user_id']) == int(data['curr_user_id']) )
        except KeyError:
            raise
        except:
            return False


    def is_deleted_post(self, prev_post_info: dict, data: dict):
        """
        fmt `prev_post_info`:
            { 'prev_post_id' : int, 'prev_post_time' : str, 'prev_post_user_id' : int }

        fmt `data`:
            {
                'curr_post_id'   : int,
                'prev_post_id'   : int,
                'curr_post_time' : int,
                'prev_post_time' : int,
                'curr_user_id'   : int,
                'prev_user_id'   : int,
                'curr_user_name' : str,
                'prev_user_name' : str
            }
        """
        if not prev_post_info:
            return False

        try: return ( str(prev_post_info['prev_post_time']) != str(data['prev_post_time']) )
        except:
            return False


    def generate_log_line(self, data: dict, log_list: list[dict] = None):
        """
        fmt `data`:
            { 'time' : str, 'user_name : str, 'added_score' : float, 'total_score' : float }
        """
        # needed only to determine the spacing size to align text
        if isinstance(log_list, type(None)):
            log_list = self.get_log_list(self.DB_TYPE_ALLTIME)

        longest_username = 0
        for log in log_list:
            longest_username = max(longest_username, len(log['user_name']))

        longest_score = 0
        for log in log_list:
            longest_score = max(longest_score, len(str(abs(float(log['added_score'])))))

        log_fmt = '[ {0} ]    {1:<%d}  {2:<%d}  | Total Score: {3}' % (longest_username, longest_score + 1)

        sign = '+' if float(data['added_score']) >= 0 else ''
        return log_fmt.format(
            data['time'],
            data['user_name'],
            sign + str(data['added_score']),
            data['score_alltime']
        )


    def get_forum_log_text(self, db_type: int):
        log_list = self.get_log_list(db_type)
        log_text = ''

        # Generate log lines
        for log_data in reversed(log_list[:]):
            log_text += self.generate_log_line(log_data, log_list) + '\n'

        if log_text == '':
            log_text = 'N/A'

        return log_text


    def get_top_scores_text(self, db_type: int):
        top_scores_list = self.get_top_scores_list(db_type)

        longest_username = 0
        for top_score in top_scores_list:
            longest_username = max(longest_username, len(top_score['user_name']))

        top_scores_format = '#{0:<%d} {1} {2:<%d}: {3} pts' % (2, longest_username)
        top_scores_text   = ''

        for i in range(len(top_scores_list)):
            text = top_scores_format.format(i + 1, top_scores_list[i]['time'], top_scores_list[i]['user_name'] , top_scores_list[i]['added_score'])
            top_scores_text += text + '\n'

        if top_scores_text == '':
            top_scores_text = 'N/A'

        return top_scores_text


    def get_top_10_text(self, db_type: int):
        pts_key = 'points_alltime' if ( db_type == self.DB_TYPE_ALLTIME ) else 'points_monthly'
        top_10_list = self.get_top_10_list(db_type)

        longest_username = 0
        for user in top_10_list:
            longest_username = max(longest_username, len(user['user_name']))

        top_10_format = '#{0:<%d} {1:<%d}: {2} pts' % (2, longest_username)
        top_10_text   = ''

        for i in range(len(top_10_list)):
            text = top_10_format.format(i + 1, top_10_list[i]['user_name'], top_10_list[i][pts_key])
            top_10_text += text + '\n'

        if top_10_text == '':
            top_10_text = 'N/A'

        return top_10_text


    def get_monthly_winners_text(self):
        monthly_winners_list = self.get_monthly_winners_list()

        longest_username = 0
        for user in monthly_winners_list:
            longest_username = max(longest_username, len(user['user_name']))

        monthly_winners_format = '{0} {1:<%d}: {2} pts' % (longest_username)
        monthly_winners_text   = ''

        # Generate log lines
        for monthly_winner in monthly_winners_list[:]:
            monthly_winners_text += monthly_winners_format.format(monthly_winner['time'], monthly_winner['user_name'], monthly_winner['points_monthly']) + '\n'

        if monthly_winners_text == '':
            monthly_winners_text = 'N/A'

        return monthly_winners_text


    class BotCmd(Cmd):

        def __init__(self, obj: "ThreadNecroBot"):
            Cmd.__init__(self, obj)
            self.obj: "ThreadNecroBot"


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
        def cmd_help(self) -> dict:
            return Cmd.ok('To be implemented...')


        @Cmd.help(
        perm = Cmd.PERMISSION_PUBLIC,
        info = 'Prints the number of points the specified user has',
        args = {
            'user_name' : Cmd.arg(str, False, 'Name of the user to print the number of point of')
        })
        def cmd_get_user_points(self, user_name: str) -> dict:
            """
            fmt DB:
                "userdata" : {
                    [user_id:int] : { 'points_alltime' : float, 'points_monthly' : float, 'user_name' : str, 'post_id' : int },
                    [user_id:int] : { 'points_alltime' : float, 'points_monthly' : float, 'user_name' : str, 'post_id' : int },
                    ...
                }
            """
            entry = self.obj.get_user(user_name)
            if not entry:
                return Cmd.err(f'Unable to find user "{user_name}"')

            return Cmd.ok(f'{user_name} | all time: {entry["points_alltime"]} pts   monthly: {entry["points_monthly"]}')


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Adds the specified number of points to the user specified or subtracts if the value is negative',
        args = {
            'user_name' : Cmd.arg(str,   False, 'Name of the user to add or take points from'),
            'points'    : Cmd.arg(float, False, 'Number of points to add'),
        })
        def cmd_add_user_points(self, cmd_key: tuple[int, int], user_name: str, points: float) -> dict:
            """
            fmt DB:
                "userdata" : {
                    [user_id:int] : { 'points_alltime' : float, 'points_monthly' : float, 'user_name' : str, 'post_id' : int },
                    [user_id:int] : { 'points_alltime' : float, 'points_monthly' : float, 'user_name' : str, 'post_id' : int },
                    ...
                }
            """
            if not self.validate_request(cmd_key):
                return Cmd.err('Insufficient permissions')

            # Request
            entry = self.obj.get_user(user_name)
            if not entry:
                return Cmd.err(f'Unable to find user "{user_name}"')

            self.obj.update_user_data({
                'user_id'     : entry.doc_id,
                'user_name'   : entry['user_name'],
                'post_id'     : entry['post_id'],
                'added_score' : float(f'{float(points):.3f}'),
            })
            self.obj.update_log_data({
                'time'        : str(ThreadNecroBotCore.LOG_TIMESTAMP_ADMIN),
                'user_id'     : entry.doc_id,
                'user_name'   : entry['user_name'],
                'post_id'     : entry['post_id'],
                'added_score' : float(f'{float(points):.3f}'),
            })

            entry = self.obj.get_user(user_name)
            msg = f'Updated user "{user_name}": {entry["points_alltime"]} pts all time, {entry["points_monthly"]} pts monthly'

            try: self.obj.write_post()
            except Exception as e:
                msg += f'\nWarning: Error writing post ({type(e).__name__}: {e})'

            return Cmd.ok(msg)


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Gets the info of the previous post recorded',
        args = {
        })
        def cmd_get_prev_post_info(self, cmd_key: tuple[int, int]) -> dict:
            if not self.validate_request(cmd_key):
                return Cmd.err(f'Insufficient permissions')

            return Cmd.ok(str(self.obj.get_prev_post_info(self.obj.get_db_table)))


        @Cmd.help(
        perm = Cmd.PERMISSION_ADMIN,
        info = 'Bans the user with the given user id from the game',
        args = {
            'user_id' : Cmd.arg(int, False, 'User id')
        })
        def cmd_ban(self, cmd_key: tuple[int, int], user_id: int) -> dict:
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
        def cmd_unban(self, cmd_key: tuple[int, int], user_id: int) -> dict:
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
        def cmd_get_user_rank(self, user_id: int) -> dict:
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
        def cmd_get_banned(self, user_id: int) -> dict:
            return Cmd.ok(str(self.obj.banned))
