import math
import logging
import datetime

import tinydb
from tinydb import table


class ThreadNecroBotCore():

    logger = logging.getLogger('ThreadNecroBot')

    DB_TYPE_MONTHLY = 0
    DB_TYPE_ALLTIME = 1

    __LOG_TIMESTAMPS = [
        '          ADMIN          ',
        '          BONUS          ',
        '       MULTI POST        ',
        '      DELETED POST       '
    ]

    __ID_TIMESTAMP_ADMIN = 0
    __ID_TIMESTAMP_BONUS = 1
    __ID_TIMESTAMP_MULTI = 2
    __ID_TIMESTAMP_DELET = 3

    LOG_TIMESTAMP_ADMIN = __LOG_TIMESTAMPS[__ID_TIMESTAMP_ADMIN]
    LOG_TIMESTAMP_BONUS = __LOG_TIMESTAMPS[__ID_TIMESTAMP_BONUS]
    LOG_TIMESTAMP_MULTI = __LOG_TIMESTAMPS[__ID_TIMESTAMP_MULTI]
    LOG_TIMESTAMP_DELET = __LOG_TIMESTAMPS[__ID_TIMESTAMP_DELET]

    __DB_FILE_LOGS          = 'ThreadNecroBot_DataLogs.json'
    __DB_FILE_WINNERS       = 'ThreadNecroBot_DataWinners.json'
    __DB_FILE_SCORES        = 'ThreadNecroBot_DataScores.json'
    __DB_FILE_USERS         = 'ThreadNecroBot_DataUsers.json'
    __DB_FILE_META          = 'ThreadNecroBot_DataMeta.json'

    __TABLE_LOGS            = 'log_data'
    __TABLE_LOGS_META       = 'log_data_meta'
    __TABLE_SCORES_ALLTIME  = 'top_scores'
    __TABLE_SCORES_MONTHLY  = 'top_scores_monthly'
    __TABLE_WINNERS         = 'monthly_winners'
    __TABLE_USERS           = 'userdata'
    __TABLE_META_PREV_POST  = 'prevpost'
    __TABLE_META_IDX        = 'idx'

    __MAX_ENTRIES_LOGS      = 10
    __MAX_ENTRIES_TOP_SCORE = 10

    def __init__(self, db_path: str):
        self.__db_path = db_path
        self.banned = []

        self._n = math.log(2000.0/60.0)/math.log(24)
        self._b = 60.0/math.pow(60.0, self._n)

        self.multi_post_pts_penalty = 100


    # def get_timestamp(self, log_timestamp: str):
    #     if log_timestamp >= len(ThreadNecroBotCore.log_timestamp):
    #         return None

    #     try: return ThreadNecroBotCore.log_timestamp[log_timestamp]
    #     except:
    #         return None


    def update_user_data(self, user_data: dict):
        """
        Operations:
        - Creates a user entry based on user id if it does not already exist. Starts at 0 pts if does not exist
        - Add `user_data['added_score']` amount of points to the user entry
        - Updates user entry's username
        - Updates user entry's last processed post id

        fmt `user_data`:
            { 'added_score' : float, 'user_id' : int, 'user_name' : str, 'post_id' : int }

        fmt DB:
            "userdata" : {
                [user_id:int] : { 'points_alltime' : float, 'points_monthly' : float, 'user_name' : str, 'post_id' : int },
                [user_id:int] : { 'points_alltime' : float, 'points_monthly' : float, 'user_name' : str, 'post_id' : int },
                ...
            }
        """
        points_alltime = self.get_user_points(user_data['user_id'], self.DB_TYPE_ALLTIME)
        points_alltime += float(user_data['added_score'])
        points_alltime = f'{points_alltime:.3f}'

        points_monthly = self.get_user_points(user_data['user_id'], self.DB_TYPE_MONTHLY)
        points_monthly += float(user_data['added_score'])
        points_monthly = f'{points_monthly:.3f}'

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_USERS}') as db:
            table_user = db.tables(self.__TABLE_USERS)
            table_user.upsert(table.Document(
                {
                    'points_alltime' : float(points_alltime),
                    'points_monthly' : float(points_monthly),
                    'user_name'      : str(user_data['user_name']),
                    'post_id'        : int(user_data['post_id'])
                },
                doc_id = int(user_data['user_id'])
            ))


    def update_log_data(self, log_data: dict):
        """
        Operations:
        1. Resolve `db_type` to table
        2. Use index in log table meta to determine which entry in log table to update
        3. Update log table entry and increment (or wrap) log table meta entry index

        fmt `log_data`:
            { time' : str, 'user_name' : str, 'user_id' : int, 'post_id' : int, 'added_score' : float, 'total_score' : float' }

        fmt DB:
            "log_data" : {
                [idx:int] : { 'time' : str, 'user_name' : str, 'user_id' : int, 'post_id' : int, 'added_score' : float, 'score_alltime' : float, 'score_monthly' : float },
                [idx:int] : { 'time' : str, 'user_name' : str, 'user_id' : int, 'post_id' : int, 'added_score' : float, 'score_alltime' : float, 'score_monthly' : float },
                ...
            },
            "log_data_meta : {
                [type:int] : { 'num' : int },
            }
        """
        score_alltime = self.get_user_points(log_data['user_id'], self.DB_TYPE_ALLTIME)
        score_monthly = self.get_user_points(log_data['user_id'], self.DB_TYPE_MONTHLY)

        num = 0

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_LOGS}') as db:
            table_meta = db.table(self.__TABLE_LOGS_META)

            entry = table_meta.get(doc_id=self.DB_TYPE_MONTHLY)
            try:  num = entry['num']
            except ( KeyError, TypeError ):
                pass

            log_data.update({
                'score_alltime' : score_alltime,
                'score_monthly' : score_monthly
            })

            table_log = db.table(self.__TABLE_LOGS)
            table_log.insert(log_data)

            num = min(num + 1, self.__MAX_ENTRIES_LOGS)
            table_meta.update(table.Document({ 'num' : num }, doc_id=self.DB_TYPE_MONTHLY))

        log_list = self.get_log_list(self.DB_TYPE_ALLTIME)
        self.logger.info(self.generate_log_line(log_data, log_list))


    def update_top_score_data(self, new_score_data: dict):
        """
        Operations:
        - Inserts a new added score entry
        - Removes lowest added score entry if reached max entries limit

        fmt `new_score_data`:
            { 'time' : str, 'user_id' : str, 'user_name' : str, 'post_id' : int, 'added_score' : float }

        fmt DB:
            "top_scores", "top_scores_monthly" : {
                [idx:int] : { 'time' : str, 'user_id' : int, 'user_name' : str, 'post_id' : int, 'added_score' : float },
                [idx:int] : { 'time' : str, 'user_id' : int, 'user_name' : str, 'post_id' : int, 'added_score' : float },
                ...
            }
        """
        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_SCORES}') as db:
            for table_name in [ self.__TABLE_SCORES_ALLTIME, self.__TABLE_SCORES_MONTHLY ]:
                table_scores = db.table(table_name)

                if len(table) < self.__MAX_ENTRIES_TOP_SCORE:
                    table_scores.insert(new_score_data)
                    return

                entries = table_scores.all()

                min_idx = min(range(len(entries)), key=lambda i: float(entries.__getitem__(i)['added_score']))
                min_val = float(entries[min_idx]['added_score'])

                is_old_score_greater = (float(new_score_data['added_score']) <= min_val)
                if is_old_score_greater:
                    return

                table_scores.upsert(table.Document(new_score_data, doc_id=min_idx))


    def update_monthly_winners(self):
        """
        Operations:
        1. Get top 10 scores and determine which entry is #1
        2. Append entry to winners list
        3. Update table

        'monthly_winners' : {
            [idx:int] : { 'time' : str, 'user_id' : int, 'points' : float, 'user_name' : str},
            [idx:int] : { 'time' : str, 'user_id' : int, 'points' : float, 'user_name' : str},
            ...
        }
        """
        monthly_winners_list: list[table.Document] = self.get_monthly_winners_list()

        # If the monthly winners list doesn't exist, that means we are doing this for the first time
        # Grab the All-time top 10 if that is so because monthly top 10 is incomplete
        if not monthly_winners_list:
            top_10_monthly_list = self.get_top_10_list(self.DB_TYPE_ALLTIME)
        else:
            top_10_monthly_list = self.get_top_10_list(self.DB_TYPE_MONTHLY)

        # Process
        if not top_10_monthly_list:
            return

        monthly_winner = top_10_monthly_list[0]
        monthly_winner['time'] = str(datetime.datetime.now().date())

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_WINNERS}') as db:
            table_winners = db.table(self.__TABLE_WINNERS)
            table_winners.insert(monthly_winner)


    def update_metadata(self):
        """
        "prevpost" : {
            [id:int] : { 'prev_post_id' : int, 'prev_post_time' : str, 'prev_post_user_id' : int },
            ...
        }
        """


    def get_user_points(self, user_id: str | int, type_id: int) -> float:
        """
        "userdata" : {
            [user_id:int] : { 'points_alltime' : float, 'points_monthly' : float, 'user_name' : str, 'post_id' : int },
            [user_id:int] : { 'points_alltime' : float, 'points_monthly' : float, 'user_name' : str, 'post_id' : int },
            ...
        }
        """
        key_id = 'points_alltime' if type_id == self.DB_TYPE_ALLTIME else 'points_monthly'

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_USERS}') as db:
            table_users = db.table(self.__TABLE_USERS)
            entry = table_users.get(doc_id=int(user_id))

            try: return entry[key_id]
            except ( TypeError, KeyError ):
                return 0


    def get_user_rank(self, user_id: str | int, type_id: int) -> int:
        """
        "userdata" : {
            [user_id:int] : { 'points_alltime' : float, 'points_monthly' : float, 'user_name' : str, 'post_id' : int },
            [user_id:int] : { 'points_alltime' : float, 'points_monthly' : float, 'user_name' : str, 'post_id' : int },
            ...
        }
        """
        key_id = 'points_alltime' if type_id == self.DB_TYPE_ALLTIME else 'points_monthly'

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_USERS}') as db:
            table_users = db.table(self.__TABLE_USERS)

            entries = table_users.all()
            ranked_uids = list([
                int(entry.doc_id) for entry in
                sorted(
                    entries,
                    key = lambda entry: float(entry[key_id]),
                    reverse = True
                )
            ])

            try: rank = ranked_uids.index(int(user_id)) + 1
            except ValueError:
                return None

            return rank


    def get_log_list(self, db_type: int) -> "list[table.Document]":
        """
        fmt DB:
            'log_data' : {
                [idx:int] : { 'time' : str, 'user_name' : str, 'user_id' : int, 'post_id' : int, 'added_score' : float, 'score_alltime' : float, 'score_monthly' : float },
                [idx:int] : { 'time' : str, 'user_name' : str, 'user_id' : int, 'post_id' : int, 'added_score' : float, 'score_alltime' : float, 'score_monthly' : float },
                ...
            },
            "log_data_meta : {
                [type:int] : { 'num' : int },
            }
        """
        num = self.__MAX_ENTRIES_LOGS

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_LOGS}') as db:
            if db_type == self.DB_TYPE_MONTHLY:
                table_log = db.table(self.__TABLE_LOGS_META)
                entry = table_log.get(doc_id=int(db_type))

                try: num = entry['num']
                except ( KeyError, TypeError ):
                    pass

            table_log = db.table(self.__TABLE_LOGS)
            lst_len   = len(table_log)

            return [
                table_log.get(doc_id=i)
                for i in range(lst_len - 1, lst_len - num - 1, -1)
            ]


    def get_top_scores_list(self, db_type: int) -> "list[table.Document]":
        """
        fmt DB:
            "top_scores" : {
                [idx:int] : { 'time' : str, 'user_id' : int, 'user_name' : str, 'post_id' : int, 'added_score' : float },
                [idx:int] : { 'time' : str, 'user_id' : int, 'user_name' : str, 'post_id' : int, 'added_score' : float },
                ...
            },
            "top_scores_monthly" : {
                [idx:int] : { 'time' : str, 'user_id' : int, 'user_name' : str, 'post_id' : int, 'added_score' : float },
                [idx:int] : { 'time' : str, 'user_id' : int, 'user_name' : str, 'post_id' : int, 'added_score' : float },
                ...
            }
        """
        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_SCORES}') as db:
            table_scores = db.table(
                self.__TABLE_SCORES_ALLTIME if db_type == self.DB_TYPE_ALLTIME else self.__TABLE_SCORES_MONTHLY
            )

            return sorted(
                table_scores.all(),
                key = lambda entry: float(entry['added_score']),
                reverse = True
            )


    def get_top_10_list(self, type_id: int) -> "list[table.Document]":
        """
        fmt DB:
            "userdata" : {
                [user_id:int] : { 'points_alltime' : float, 'points_monthly' : float, 'user_name' : str, 'post_id' : int },
                [user_id:int] : { 'points_alltime' : float, 'points_monthly' : float, 'user_name' : str, 'post_id' : int },
                ...
            }
        """
        key_id = 'points_alltime' if type_id == self.DB_TYPE_ALLTIME else 'points_monthly'

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_USERS}') as db:
            ranked_entries = sorted(
                db.all(),
                key = lambda entry: float(entry[key_id]),
                reverse = True
            )

            return ranked_entries[:10]


    def get_monthly_winners_list(self) -> "list[table.Document]":
        """
        fmt DB:
            'monthly_winners' : {
                [idx:int] : { 'time' : str, 'user_id' : int, 'points' : float, 'user_name' : str},
                [idx:int] : { 'time' : str, 'user_id' : int, 'points' : float, 'user_name' : str},
                ...
            }
        """
        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_WINNERS}') as db:
            table_winners = db.table(self.__TABLE_WINNERS)
            return table_winners.all()


    def reset_monthly_data(self):
        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_SCORES}') as db:
            table_scores = db.table(self.__TABLE_SCORES_MONTHLY)
            table_scores.truncate()

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_LOGS}') as db:
            table_logs = db.table(self.__TABLE_LOGS)


    def generate_log_line(self, log_data: dict, log_list: "list[dict]"):
        sign = '+' if float(log_data['added_score']) >= 0 else ''
        return self.generate_log_format(log_list).format(
            log_data['time'],
            log_data['user_name'],
            sign + str(log_data['added_score']),
            log_data['total_score']
        )


    def generate_log_format(self, log_list: "list[dict]"):
        longest_username = 0
        for log in log_list:
            longest_username = max(longest_username, len(log['user_name']))

        longest_score = 0
        for log in log_list:
            longest_score = max(longest_score, len(str(abs(float(log['added_score'])))))

        return '[ {0} ]    {1:<%d}  {2:<%d}  | Total Score: {3}' % (longest_username, longest_score + 1)


    def get_forum_log_text(self, log_list: "list[dict]"):
        log_text = ''

        # Generate log lines
        for log_data in reversed(log_list[:]):
            log_text += self.generate_log_line(log_data, log_list) + '\n'

        if log_text == '':
            log_text = 'N/A'

        return log_text


    def get_top_scores_text(self, top_scores_list: "list[dict]"):
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


    def get_top_10_text(self, top_10_list: "list[dict]"):
        longest_username = 0
        for user in top_10_list:
            longest_username = max(longest_username, len(user['user_name']))

        top_10_format = '#{0:<%d} {1:<%d}: {2} pts' % (2, longest_username)
        top_10_text   = ''

        for i in range(len(top_10_list)):
            text = top_10_format.format(i + 1, top_10_list[i]['user_name'], top_10_list[i]['points'])
            top_10_text += text + '\n'

        if top_10_text == '':
            top_10_text = 'N/A'

        return top_10_text


    def get_monthly_winners_text(self, monthly_winners_list: "list[dict]"):
        longest_username = 0
        for user in monthly_winners_list:
            longest_username = max(longest_username, len(user['user_name']))

        monthly_winners_format = '{0} {1:<%d}: {2} pts' % (longest_username)
        monthly_winners_text   = ''

        # Generate log lines
        for monthly_winner in monthly_winners_list[:]:
            monthly_winners_text += monthly_winners_format.format(monthly_winner['time'], monthly_winner['user_name'], monthly_winner['points']) + '\n'

        if monthly_winners_text == '':
            monthly_winners_text = 'N/A'

        return monthly_winners_text


    def get_prev_post_info(self):
        """
        "prevpost" : {
            [id:int] : { 'prev_post_id' : int, 'prev_post_time' : str, 'prev_post_user_id' : int },
            ...
        }
        """
        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_META}') as db:
            table_meta = db.table(self.__TABLE_META_PREV_POST)
            return table_meta.get(None, doc_id=0)
