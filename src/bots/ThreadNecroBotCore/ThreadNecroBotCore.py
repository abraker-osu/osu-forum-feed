from typing import Union

import math
import logging
import datetime

import tinydb
from tinydb import table, TinyDB


class DB_ENUM():
    DB_TYPE_MONTHLY  = 0
    DB_TYPE_ALL_TIME = 1

    MONTHLY_LOG     = 0
    MONTHLY_USER    = 1
    MONTHLY_SCORES  = 2
    MONTHLY_WINNERS = 3

    ALL_TIME_LOG     = 10
    ALL_TIME_USER    = 11
    ALL_TIME_SCORES  = 12


class ThreadNecroBotCore():

    logger = logging.getLogger('ThreadNecroBot')

    log_timestamp = [
        '          ADMIN          ',
        '          BONUS          ',
        '       MULTI POST        ',
        '      DELETED POST       '
    ]

    ADMIN_TIMESTAMP = 0
    BONUS_TIMESTAMP = 1
    MULTI_TIMESTAMP = 2
    DELET_TIMESTAMP = 3

    MAX_LOG_ENTRIES       = 10
    MAX_TOP_SCORE_ENTRIES = 10

    def __init__(self, db_tables: "dict[int, TinyDB.table_class]"):
        if DB_ENUM.MONTHLY_LOG     not in db_tables: raise KeyError('Monthly log table not found')
        if DB_ENUM.MONTHLY_USER    not in db_tables: raise KeyError('Monthly user table not found')
        if DB_ENUM.MONTHLY_SCORES  not in db_tables: raise KeyError('Monthly scores table not found')
        if DB_ENUM.MONTHLY_WINNERS not in db_tables: raise KeyError('Monthly winners table not found')

        if DB_ENUM.ALL_TIME_LOG    not in db_tables: raise KeyError('All time log table not found')
        if DB_ENUM.ALL_TIME_USER   not in db_tables: raise KeyError('All time user table not found')
        if DB_ENUM.ALL_TIME_SCORES not in db_tables: raise KeyError('All time score table not found')

        self.db_tables: "dict[int, TinyDB.table_class]" = db_tables
        self.banned = []

        self._n = math.log(2000.0/60.0)/math.log(24)
        self._b = 60.0/math.pow(60.0, self._n)

        self.multi_post_pts_penalty = 100


    def get_timestamp(self, log_timestamp: str):
        if log_timestamp >= len(ThreadNecroBotCore.log_timestamp):
            return None

        try: return ThreadNecroBotCore.log_timestamp[log_timestamp]
        except:
            return None


    def is_multi_post(self, prev_post_info: dict, data: dict):
        if not prev_post_info:
            return False

        try: multi_post = (str(prev_post_info['user_id']) == str(data['curr_user_id']))
        except:
            multi_post = False

        return multi_post


    def is_deleted_post(self, prev_post_info: dict, data: dict):
        if not prev_post_info:
            return False

        special_event = (prev_post_info['time'] in ThreadNecroBotCore.log_timestamp)
        if special_event:
            return False

        try: deleted_post = (str(prev_post_info['time']) != str(data['prev_post_time']))
        except:
            deleted_post = False

        return deleted_post


    def update_user_data(self, user_data: dict, db_type: int):
        """
        Operations:
        - Creates a user entry based on user id if it does not already exist. Starts at 0 pts if does not
        - Add `user_data['added_score']` amount of points to the user entry
        - Updates user entry's username
        - Updates user entry's last processed post id

        db Format:
        {
            user_id : { 'points' : '...', 'user_name' : '...', 'post_id' : '...' },
            user_id : { 'points' : '...', 'user_name' : '...', 'post_id' : '...' },
            ...
        }
        """
        user_data_table = \
            self.db_tables[DB_ENUM.ALL_TIME_USER] if (db_type == DB_ENUM.DB_TYPE_ALL_TIME) else self.db_tables[DB_ENUM.MONTHLY_USER]

        # Process
        points = self.get_user_points(user_data['user_id'], db_type)
        points += float(user_data['added_score'])
        points = f'{points:.3f}'

        # Update
        user_data_table.upsert(table.Document(
            {
                'points'    : float(points),
                'user_name' : user_data['user_name'],
                'post_id'   : user_data['post_id']
            },
            doc_id = int(user_data['user_id'])
        ))


    def update_log_data(self, log_data: dict, db_type: int):
        """
        'log_data' : [
            { 'time' : '...', 'user_name' : '...', 'user_id' : '...', 'post_id' : '...', 'added_score' : '...', 'total_score' : '...', },
            { 'time' : '...', 'user_name' : '...', 'user_id' : '...', 'post_id' : '...', 'added_score' : '...', 'total_score' : '...', },
            { 'time' : '...', 'user_name' : '...', 'user_id' : '...', 'post_id' : '...', 'added_score' : '...', 'total_score' : '...', },
            ...
        ]
        """
        # Request
        log_data_table = \
            self.db_tables[DB_ENUM.ALL_TIME_LOG] if (db_type == DB_ENUM.DB_TYPE_ALL_TIME) else self.db_tables[DB_ENUM.MONTHLY_LOG]

        log_list = self.get_log_list(db_type)

        # Process
        if log_list:
            # Log is a FIFO of 10 entries
            if len(log_list) >= self.MAX_LOG_ENTRIES:
                log_data_table.remove(doc_ids=[ log_list[0].doc_id ])

        log_data_table.insert(log_data)

        if db_type == DB_ENUM.DB_TYPE_ALL_TIME:
            self.logger.info(self.generate_log_line(log_data, log_list))


    def update_top_score_data(self, new_score_data: dict, db_type: int):
        """
        Operations:
        - Inserts a new added score entry
        - Removes lowest added score entry if reached max entries limit

        db format:
        {
            { 'time' : '...', 'user_id' : '...', 'user_name' : '...', 'post_id' : '...', 'added_score' : '...' },
            { 'time' : '...', 'user_id' : '...', 'user_name' : '...', 'post_id' : '...', 'added_score' : '...' },
            ...
        }
        """
        # Request
        score_data_table = \
            self.db_tables[DB_ENUM.ALL_TIME_SCORES] if (db_type == DB_ENUM.DB_TYPE_ALL_TIME) else self.db_tables[DB_ENUM.MONTHLY_SCORES]

        # Process
        top_scores_entries = score_data_table.all()

        if len(score_data_table) < self.MAX_TOP_SCORE_ENTRIES:
            score_data_table.insert(new_score_data)
            return

        lowest_added_score_idx = min(range(len(top_scores_entries)), key=lambda i: float(top_scores_entries.__getitem__(i)['added_score']))
        lowest_added_score_val = float(top_scores_entries[lowest_added_score_idx]['added_score'])

        is_old_score_greater = (float(new_score_data['added_score']) <= lowest_added_score_val)
        if is_old_score_greater:
            return

        score_data_table.remove(doc_ids=[ top_scores_entries[lowest_added_score_idx].doc_id ])
        score_data_table.insert(new_score_data)


    def update_monthly_winners(self):
        """
        'monthly_winners' : [
            { 'time' : '...', 'user_id' : '...', 'points' : '...', 'user_name' : '...'},
            { 'time' : '...', 'user_id' : '...', 'points' : '...', 'user_name' : '...'},
            ...
        ]
        """
        # Request
        score_data_table = self.db_tables[DB_ENUM.MONTHLY_WINNERS]
        monthly_winners_list: list[table.Document] = self.get_monthly_winners_list()

        # If the monthly winners list doesn't exist, that means we are doing this for the first time
        # Grab the All-time top 10 if that is so because monthly top 10 is incomplete
        if not monthly_winners_list:
            top_10_monthly_list = self.get_top_10_list(DB_ENUM.DB_TYPE_ALL_TIME)
        else:
            top_10_monthly_list = self.get_top_10_list(DB_ENUM.DB_TYPE_MONTHLY)

        # Process
        if not top_10_monthly_list:
            return

        monthly_winner = top_10_monthly_list[0]
        monthly_winner['time'] = str(datetime.datetime.now().date())

        score_data_table.insert(monthly_winner)


    def get_user_points(self, user_id: Union[str, int], db_type: int) -> float:
        """
        {
            user_id : { 'points' : '...', 'user_name' : '...', 'post_id' : '...' },
            user_id : { 'points' : '...', 'user_name' : '...', 'post_id' : '...' },
            ...
        }
        """
        user_data_table = \
            self.db_tables[DB_ENUM.ALL_TIME_USER] if (db_type == DB_ENUM.DB_TYPE_ALL_TIME) else self.db_tables[DB_ENUM.MONTHLY_USER]

        entry = user_data_table.get(doc_id=int(user_id))
        if isinstance(entry, type(None)):
            return 0

        if not 'points' in entry:
            return 0

        return entry['points']


    def get_user_rank(self, user_id: Union[str, int], db_type: int) -> int:
        """
        {
            user_id : { 'points' : '...', 'user_name' : '...', 'post_id' : '...' },
            user_id : { 'points' : '...', 'user_name' : '...', 'post_id' : '...' },
            ...
        }
        """
        user_data_table = \
            self.db_tables[DB_ENUM.ALL_TIME_USER] if (db_type == DB_ENUM.DB_TYPE_ALL_TIME) else self.db_tables[DB_ENUM.MONTHLY_USER]

        entries = user_data_table.all()
        ranked_uids = list([
            int(entry.doc_id) for entry in
            sorted(
                entries,
                key = lambda entry: float(entry['points']),
                reverse = True
            )
        ])

        try: rank = ranked_uids.index(int(user_id)) + 1
        except ValueError:
            rank = None

        return rank


    def get_log_list(self, db_type: int) -> "list[table.Document]":
        """
        'log_data' : [
            { 'time' : '...', 'user_name' : '...', 'user_id' : '...', 'post_id' : '...', 'added_score' : '...', 'total_score' : '...', },
            { 'time' : '...', 'user_name' : '...', 'user_id' : '...', 'post_id' : '...', 'added_score' : '...', 'total_score' : '...', },
            { 'time' : '...', 'user_name' : '...', 'user_id' : '...', 'post_id' : '...', 'added_score' : '...', 'total_score' : '...', },
            ...
        ]
        """
        log_data_table = \
            self.db_tables[DB_ENUM.ALL_TIME_LOG] if (db_type == DB_ENUM.DB_TYPE_ALL_TIME) else self.db_tables[DB_ENUM.MONTHLY_LOG]

        return log_data_table.all()


    def get_top_scores_list(self, db_type: int) -> "list[table.Document]":
        """
        {
            { 'time' : '...', 'user_id' : '...', 'user_name' : '...', 'post_id' : '...', 'added_score' : '...' },
            { 'time' : '...', 'user_id' : '...', 'user_name' : '...', 'post_id' : '...', 'added_score' : '...' },
            ...
        }
        """
        scores_data_table = \
            self.db_tables[DB_ENUM.ALL_TIME_SCORES] if (db_type == DB_ENUM.DB_TYPE_ALL_TIME) else self.db_tables[DB_ENUM.MONTHLY_SCORES]

        return sorted(
            scores_data_table.all(),
            key = lambda entry: float(entry['added_score']),
            reverse = True
        )


    def get_top_10_list(self, db_type: int) -> "list[table.Document]":
        user_data_table = \
            self.db_tables[DB_ENUM.ALL_TIME_USER] if (db_type == DB_ENUM.DB_TYPE_ALL_TIME) else self.db_tables[DB_ENUM.MONTHLY_USER]

        ranked_entries = sorted(
            user_data_table.all(),
            key = lambda entry: float(entry['points']),
            reverse = True
        )

        return ranked_entries[:10]


    def get_monthly_winners_list(self) -> "list[table.Document]":
        """
        'monthly_winners' : [
            { 'time' : '...', 'user_id' : '...', 'points' : '...', 'user_name' : '...'},
            { 'time' : '...', 'user_id' : '...', 'points' : '...', 'user_name' : '...'},
            ...
        ]
        """
        score_data_table = self.db_tables[DB_ENUM.MONTHLY_WINNERS]
        return score_data_table.all()


    def reset_monthly_data(self):
        self.db_tables[DB_ENUM.MONTHLY_USER].truncate()
        self.db_tables[DB_ENUM.MONTHLY_LOG].truncate()
        self.db_tables[DB_ENUM.MONTHLY_SCORES].truncate()


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
        log_data_table = self.db_tables[DB_ENUM.ALL_TIME_LOG]
        return log_data_table.all()[-1]
