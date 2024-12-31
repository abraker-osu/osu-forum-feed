import os
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
    __TABLE_USERS_DATA      = 'user_data'
    __TABLE_USERS_ALLTIME   = 'user_points_alltime'
    __TABLE_USERS_MONTHLY   = 'user_points_monthly'
    __TABLE_META_PREV_POST  = 'prevpost'

    __MAX_ENTRIES_LOGS      = 10
    __MAX_ENTRIES_TOP_SCORE = 100

    def __init__(self, db_path: str):
        self.__db_path = db_path
        self.banned = []

        self._n = math.log(2000.0/60.0)/math.log(24)
        self._b = 60.0/math.pow(60.0, self._n)

        os.makedirs(self.__db_path, mode=0o660, exist_ok=True)


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
            "user_data" : {
                [user_id:int] : { 'user_name' : str, 'post_id' : int },
                [user_id:int] : { 'user_name' : str, 'post_id' : int },
                ...
            },
            "user_points_alltime" : {
                [user_id:int] : { 'points' : float },
                [user_id:int] : { 'points' : float },
                ...
            },
            "user_points_monthly" : {
                [user_id:int] : { 'points' : float },
                [user_id:int] : { 'points' : float },
                ...
            }
        """
        points_alltime = self.get_user_points(user_data['user_id'], self.DB_TYPE_ALLTIME)
        points_alltime += float(user_data['added_score'])
        points_alltime = f'{points_alltime:.3f}'

        points_monthly = self.get_user_points(user_data['user_id'], self.DB_TYPE_MONTHLY)
        points_monthly += float(user_data['added_score'])
        points_monthly = f'{points_monthly:.3f}'

        uid = int(user_data['user_id'])

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_USERS}') as db:
            table_user = db.table(self.__TABLE_USERS_DATA)

            data = {}
            data['post_id'] = int(user_data['post_id'])
            if 'user_name' in user_data:
                # NOTE: This might leave username blank in some edge cases
                data['user_name'] = user_data['user_name']
            table_user.upsert(table.Document(data, doc_id = uid))

            table_user = db.table(self.__TABLE_USERS_ALLTIME)
            table_user.upsert(table.Document({
                'points' : float(points_alltime),
            }, doc_id = uid))

            table_user = db.table(self.__TABLE_USERS_MONTHLY)
            table_user.upsert(table.Document({
                'points' : float(points_monthly)
            }, doc_id = uid))


    def update_log_data(self, log_data: dict):
        """
        Operations:
        1. Resolve `db_type` to table
        2. Use index in log table meta to determine which entry in log table to update
        3. Update log table entry and increment (or wrap) log table meta entry index

        fmt `log_data`:
            { time' : str, 'user_name' : str, 'user_id' : int, 'post_id' : int, 'added_score' : float }

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

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_LOGS}') as db:
            table_meta = db.table(self.__TABLE_LOGS_META)

            # Get number of monthly log entries
            entry = table_meta.get(doc_id=self.DB_TYPE_MONTHLY)

            try:
                if not isinstance(entry, table.Document):
                    raise TypeError

                num = entry['num']
            except ( KeyError, TypeError ):
                num = 0

            # Update num metadata entry
            table_meta.update(table.Document({ 'num' : num + 1 }, doc_id=self.DB_TYPE_MONTHLY))

            # Add log entry
            log_data.update({
                'score_alltime' : score_alltime,
                'score_monthly' : score_monthly
            })

            table_log = db.table(self.__TABLE_LOGS)
            table_log.insert(log_data)


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

                # Limit number of top scores in db
                if len(table_scores) < self.__MAX_ENTRIES_TOP_SCORE:
                    table_scores.insert(table.Document(new_score_data, doc_id=len(table_scores)))
                    return

                # Search for lowest added score and replace if new score is greater
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
        1. Get top 10 scores and determine which entry is #1 (record entry as "no winner" if list is empty)
        2. Append entry to winners list
        3. Update table

        fmt DB:
            'monthly_winners' : {
                [idx:int] : { 'time' : str, 'user_id' : int, 'user_name' : str, 'points' : float },
                [idx:int] : { 'time' : str, 'user_id' : int, 'user_name' : str, 'points' : float },
                ...
            }
        """
        # Default if monthly ranked list is empty
        # fmt entry (`self.get_ranked_list`):
        #     { 'user_name' : str, 'points' : float }
        monthly_winner = table.Document({
            'user_name' : 'No Winner',
            'points'    : 0.0
        }, doc_id=-1)

        # If the monthly winners list doesn't exist, that means we are doing this for the first time
        # Grab the All-time top 10 if that is so because monthly top 10 is incomplete
        top_scores_list = self.get_ranked_list(self.DB_TYPE_MONTHLY)
        if len(top_scores_list) != 0:
            monthly_winner = top_scores_list[0]

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_WINNERS}') as db:
            table_winners = db.table(self.__TABLE_WINNERS)
            table_winners.upsert(table.Document({
                'time'      : str(datetime.datetime.now().date()),
                'user_id'   : monthly_winner.doc_id,
                'user_name' : monthly_winner['user_name'],
                'points'    : monthly_winner['points'],
            }, len(table_winners)))


    def update_metadata(self, data: dict):
        """
        fmt `data`:
            { 'time' : str, 'user_id' : str, 'user_name' : str, 'post_id' : int, 'added_score' : float }

        fmt DB:
            "prevpost" : {
                [id:int] : { 'prev_post_id' : int, 'prev_post_time' : str, 'prev_post_user_id' : int },
                ...
            }
        """
        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_META}') as db:
            table_meta = db.table(self.__TABLE_META_PREV_POST)
            table_meta.upsert(table.Document({
                'prev_post_id'        : data['post_id'],
                'prev_post_time'      : data['time'],
                'prev_post_user_id'   : data['user_id'],
                'prev_post_user_name' : data['user_name'],
            }, doc_id=0))


    def get_user(self, user_name: str) -> table.Document | None:
        """
        fmt DB:
            "user_data" : {
                [user_id:int] : { 'user_name' : str, 'post_id' : int },
                [user_id:int] : { 'user_name' : str, 'post_id' : int },
                ...
            },
            "user_points_alltime" : {
                [user_id:int] : { 'points' : float },
                [user_id:int] : { 'points' : float },
                ...
            },
            "user_points_monthly" : {
                [user_id:int] : { 'points' : float },
                [user_id:int] : { 'points' : float },
                ...
            }
        """
        query = tinydb.Query()

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_USERS}') as db:
            table_users = db.table(self.__TABLE_USERS_DATA)
            entry_user_data = table_users.get(query['user_name'] == user_name)
            if not isinstance(entry_user_data, table.Document):
                return None

        return entry_user_data


    def get_user_points(self, user_id: str | int, type_id: int) -> float:
        """
        Gets the number of points the user has from the database

        fmt DB:
            "user_data" : {
                [user_id:int] : { 'user_name' : str, 'post_id' : int },
                [user_id:int] : { 'user_name' : str, 'post_id' : int },
                ...
            },
            "user_points_alltime" : {
                [user_id:int] : { 'points' : float },
                [user_id:int] : { 'points' : float },
                ...
            },
            "user_points_monthly" : {
                [user_id:int] : { 'points' : float },
                [user_id:int] : { 'points' : float },
                ...
            }

        Parameters
        ----------
        user_id : str | int
            The id of the user

        type_id : int
            The type of points to get
            - (0) self.DB_TYPE_ALLTIME: Retrieves all time top scores
            - (1) self.DB_TYPE_MONTHLY: Retrieves monthly top scores

        Returns
        -------
        float
            The number of points the user has
        """
        table_db = self.__TABLE_USERS_ALLTIME if type_id == self.DB_TYPE_ALLTIME else self.__TABLE_USERS_MONTHLY

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_USERS}') as db:
            table_users = db.table(table_db)
            entry = table_users.get(doc_id = int(user_id))

            try:
                assert isinstance(entry, table.Document)
                return entry['points']
            except ( TypeError, KeyError, AssertionError ):
                return 0


    def get_user_rank(self, user_id: str | int, type_id: int) -> int | None:
        """
        Gets the rank of the user from the database

        fmt DB:
            "user_data" : {
                [user_id:int] : { 'user_name' : str, 'post_id' : int },
                [user_id:int] : { 'user_name' : str, 'post_id' : int },
                ...
            },
            "user_points_alltime" : {
                [user_id:int] : { 'points' : float },
                [user_id:int] : { 'points' : float },
                ...
            },
            "user_points_monthly" : {
                [user_id:int] : { 'points' : float },
                [user_id:int] : { 'points' : float },
                ...
            }

        Parameters
        ----------
        user_id : str | int
            The id of the user

        type_id : int
            The type of points to use for ranking
            - (0) self.DB_TYPE_ALLTIME: Retrieves all time top scores
            - (1) self.DB_TYPE_MONTHLY: Retrieves monthly top scores

        Returns
        -------
        int | None
            The rank of the user or None if the user is not found
        """
        table = self.__TABLE_USERS_ALLTIME if type_id == self.DB_TYPE_ALLTIME else self.__TABLE_USERS_MONTHLY

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_USERS}') as db:
            table_users = db.table(table)

            entries = table_users.all()
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
                return None

            return rank


    def get_log_list(self, db_type: int, idx: int = 0, num: int | None = None) -> list[table.Document]:
        """
        Retrieves a list of log entries from the database

        fmt DB:
            'log_data' : {
                [idx:int] : { 'time' : str, 'user_name' : str, 'user_id' : int, 'post_id' : int, 'added_score' : float, 'score_alltime' : float, 'score_monthly' : float },
                [idx:int] : { 'time' : str, 'user_name' : str, 'user_id' : int, 'post_id' : int, 'added_score' : float, 'score_alltime' : float, 'score_monthly' : float },
                ...
            },
            "log_data_meta : {
                [type:int] : { 'num' : int },
            }

        Parameters
        ----------
        db_type : int
            The type of log entries to retrieve
            - (0) self.DB_TYPE_ALLTIME: Retrieves all time top scores
            - (1) self.DB_TYPE_MONTHLY: Retrieves monthly top scores

        idx : int
            The starting index of the log entries to retrieve

        num : int
            The number of log entries to retrieve

        Returns
        -------
        list[table.Document]
            A list of log entries
        """
        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_LOGS}') as db:
            if db_type == self.DB_TYPE_MONTHLY:
                # If it's monthly, figure out how many monthly entries to retrieve
                table_log_meta = db.table(self.__TABLE_LOGS_META)
                entry = table_log_meta.get(doc_id=0)

                try:
                    if not isinstance(entry, table.Document):
                        raise TypeError

                    num = entry['num']
                except ( KeyError, TypeError ):
                    pass

            table_log = db.table(self.__TABLE_LOGS)
            lst_len   = len(table_log)

            if isinstance(num, type(None)):
                num = lst_len

            return [
                entry
                for i in range(lst_len - idx, lst_len - idx - num, -1)
                if isinstance(entry := table_log.get(doc_id = i), table.Document)
            ]


    def get_top_scores_list(self, db_type: int) -> list[table.Document]:
        """
        Retrieves a list of top scores from the database

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

        Parameters
        ----------
        db_type : int
            The type of top scores to retrieve
            - (0) self.DB_TYPE_ALLTIME: Retrieves all time top scores
            - (1) self.DB_TYPE_MONTHLY: Retrieves monthly top scores

        Returns
        -------
        list[table.Document]
            A list of top score entries

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


    def get_ranked_list(self, type_id: int) -> list[table.Document]:
        """
        Retrieves a list of users from the database ranked in order of points,
        ordered highest to lowest

        fmt DB:
            "user_data" : {
                [user_id:int] : { 'user_name' : str, 'post_id' : int },
                [user_id:int] : { 'user_name' : str, 'post_id' : int },
                ...
            },
            "user_points_alltime" : {
                [user_id:int] : { 'points' : float },
                [user_id:int] : { 'points' : float },
                ...
            },
            "user_points_monthly" : {
                [user_id:int] : { 'points' : float },
                [user_id:int] : { 'points' : float },
                ...
            }

        Parameters
        ----------
        type_id : int
            The type of points to retrieve
            - (0) self.DB_TYPE_ALLTIME: Retrieves all time top scores
            - (1) self.DB_TYPE_MONTHLY: Retrieves monthly top scores

        Returns
        -------
        list[table.Document]
            A sorted list user entries by points
            fmt:
                [
                    [user_id:int] : { 'user_name' : str, 'points' : float },
                    [user_id:int] : { 'user_name' : str, 'points' : float },
                    ...
                ]
        """
        table_name = self.__TABLE_USERS_ALLTIME if type_id == self.DB_TYPE_ALLTIME else self.__TABLE_USERS_MONTHLY

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_USERS}') as db:
            table_users = db.table(table_name)

            ranked_entries = table_users.all()
            ranked_entries.sort(key = lambda entry: float(entry['points']), reverse = True)

            table_users = db.table(self.__TABLE_USERS_DATA)
            for entry in ranked_entries:
                # Insert user name into entries
                data = table_users.get(doc_id = entry.doc_id)

                assert isinstance(data, table.Document)
                entry['user_name'] = data['user_name']

            return ranked_entries


    def get_monthly_winners_list(self) -> list[table.Document]:
        """
        Retrieves a list of monthly winners from the database

        fmt DB:
            'monthly_winners' : {
                [idx:int] : { 'time' : str, 'user_id' : int, 'points' : float, 'user_name' : str},
                [idx:int] : { 'time' : str, 'user_id' : int, 'points' : float, 'user_name' : str},
                ...
            }

        Returns
        -------
        list[table.Document]
            A list of monthly winners
        """
        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_WINNERS}') as db:
            table_winners = db.table(self.__TABLE_WINNERS)
            return table_winners.all()


    def reset_monthly_data(self):
        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_SCORES}') as db:
            table_scores = db.table(self.__TABLE_SCORES_MONTHLY)
            table_scores.truncate()

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_USERS}') as db:
            table_users = db.table(self.__TABLE_USERS_MONTHLY)
            table_users.truncate()

        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_LOGS}') as db:
            table_logs_meta = db.table(self.__TABLE_LOGS_META)
            table_logs_meta.upsert(table.Document({
                'num' : 0
            }, doc_id=0))


    def get_prev_post_info(self) -> table.Document | list[table.Document] | None:
        """
        Retrieves info of previous ThreadNecro post from the database

        fmt DB:
            "prevpost" : {
                [id:int] : { 'prev_post_id' : int, 'prev_post_time' : str, 'prev_post_user_id' : int },
                ...
            }

        Returns
        -------
        table.Document
            The previous post id, time, and user id
        """
        with tinydb.TinyDB(f'{self.__db_path}/{self.__DB_FILE_META}') as db:
            table_meta = db.table(self.__TABLE_META_PREV_POST)
            return table_meta.get(None, doc_id=0)
