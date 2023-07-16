import math
import tinydb
import datetime


class DB_ENUM():
    ALL_TIME        = 0
    MONTHLY         = 1

    LOG_DATA   = 0
    USER_DATA  = 1
    TOP_SCORES = 2
    MONTHLY_WINNERS = 3


class ThreadNecroBotCore():

    bot_db = {
        DB_ENUM.ALL_TIME : {
            DB_ENUM.LOG_DATA   : 'LogData',
            DB_ENUM.USER_DATA  : 'UserData',
            DB_ENUM.TOP_SCORES : 'TopScoresData'
        },
        DB_ENUM.MONTHLY : {
            DB_ENUM.LOG_DATA        : 'LogData_monthly',
            DB_ENUM.USER_DATA       : 'UserData_monthly',
            DB_ENUM.TOP_SCORES      : 'TopScoresData_monthly',
            DB_ENUM.MONTHLY_WINNERS : 'MonthlyWinners'
        }
    }

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
            
    def __init__(self):
        self.banned = []

        self.max_log_entries       = 10
        self.max_top_score_entries = 10

        self._n = math.log(2000.0/60.0)/math.log(24)
        self._b = 60.0/math.pow(60.0, self._n)

        self.multi_post_pts_penalty = 100


    def get_db(self, db_type, db_data):
        if not ThreadNecroBotCore.bot_db[db_type]:          raise Exception("Db type selection doesn't exist")
        if not ThreadNecroBotCore.bot_db[db_type][db_data]: raise Exception("Db data selection doesn't exist")
        
        return ThreadNecroBotCore.bot_db[db_type][db_data]


    def get_timestamp(self, log_timestamp):
        if log_timestamp >= len(ThreadNecroBotCore.log_timestamp):
            return None

        try: return ThreadNecroBotCore.log_timestamp[log_timestamp]
        except: return None


    def is_multi_post(self, logger, prev_post_info, data):
        if not prev_post_info: return False

        try:    multi_post = (str(prev_post_info['user_id']) == str(data['curr_user_id']))
        except: multi_post = False 

        return multi_post


    def is_deleted_post(self, logger, prev_post_info, data):
        if not prev_post_info: return False

        special_event = (prev_post_info['time'] in ThreadNecroBotCore.log_timestamp)
        if special_event: return False

        try:    deleted_post = (str(prev_post_info['time']) != str(data['prev_post_time']))
        except: deleted_post = False 

        return deleted_post


    def update_user_data(self, logger, db, user_data, db_type):
        # Request
        user_data_collection = db(self.get_db(db_type, DB_ENUM.USER_DATA))
        points = self.get_user_points(logger, db, user_data['user_id'], db_type)

        # Process
        points = points + float(user_data['added_score'])
        points = '%.3f'%(points)

        # Update
        query = { 'user_id' : str(user_data['user_id']) }
        value = { 'points' : float(points), 'user_name' : user_data['user_name'], 'post_id' : user_data['post_id'] }
        user_data_collection.update_one(query, { "$set" : value }, upsert=True)


    def update_log_data(self, logger, db, log_data, db_type):
        # Request
        log_data_collection = db(self.get_db(db_type, DB_ENUM.LOG_DATA))
        log_list = self.get_log_list(logger, db, db_type)

        # Process
        if not log_list: log_list = [ log_data ]
        else:
            # Log is a FIFO of 10 entries
            if len(log_list) >= self.max_log_entries: log_list.remove(log_list[0])
            log_list.append(log_data)

        if db_type == DB_ENUM.ALL_TIME:
            logger.info(self.generate_log_line(log_data, log_list))

        # Update
        query = { 'log_data' : {'$exists' : True} }
        value = log_list
        log_data_collection.update_one(query, { "$set" : { 'log_data' : value } }, upsert=True)


    def update_top_score_data(self, logger, db, new_score_data, db_type):
        # Request
        top_scores_data_collection = db(self.get_db(db_type, DB_ENUM.TOP_SCORES))
        top_scores_list = self.get_top_scores_list(logger, db, db_type)

        # Process
        if not top_scores_list: top_scores_list = [ new_score_data ]
        else:  
            max_entries_reached  = (len(top_scores_list) >= self.max_top_score_entries)
            new_score_is_greater = (float(new_score_data['added_score']) >= float(top_scores_list[-1]['added_score']))

            if max_entries_reached and new_score_is_greater:
                top_scores_list.remove(top_scores_list[-1]) # Last one is always the lowest one
                top_scores_list.append(new_score_data)
                top_scores_list = sorted(top_scores_list, key=lambda score_data: -float(score_data['added_score']))
            elif not max_entries_reached:
                top_scores_list.append(new_score_data)
                top_scores_list = sorted(top_scores_list, key=lambda score_data: -float(score_data['added_score']))
                
        # Update
        query = { 'top_scores_data' : {'$exists' : True} }
        value = top_scores_list
        top_scores_data_collection.update_one(query, { "$set" : { 'top_scores_data' : value } }, upsert=True)


    def update_monthly_winners(self, logger, db):
        # Request
        monthly_winners_data_collection = db(self.get_db(DB_ENUM.MONTHLY, DB_ENUM.MONTHLY_WINNERS))
        monthly_winners_list = self.get_monthly_winners_list(logger, db)

        # If the monthly winners list doesn't exist, that means we are doing this for the first time
        # Grab the All-time top 10 if that is so because monthly top 10 is incomplete
        if not monthly_winners_list: top_10_monthly_list = self.get_top_10_list(logger, db, DB_ENUM.ALL_TIME)    
        else:                        top_10_monthly_list = self.get_top_10_list(logger, db, DB_ENUM.MONTHLY)

        # Process
        if not top_10_monthly_list: return
        
        monthly_winner = top_10_monthly_list[0]
        monthly_winner['time'] = str(datetime.datetime.now().date())
        monthly_winners_list.append(monthly_winner)

        # Update
        query  = { 'monthly_winners' : {'$exists' : True} }
        value = monthly_winners_list
        monthly_winners_data_collection.update_one(query, { "$set" : { 'monthly_winners' : value } }, upsert=True)


    def get_user_points(self, logger, db, user_id, db_type):
        '''
        {
            { 'user_id' : '...', 'points' : '...', 'user_name' : '...', 'post_id' : '...' },
            { 'user_id' : '...', 'points' : '...', 'user_name' : '...', 'post_id' : '...' },
            ...
        }
        '''
        user_data_collection = db(self.get_db(db_type, DB_ENUM.USER_DATA))

        # Request
        query      = { 'user_id' : str(user_id) }
        projection = { 'points' : 1 }
        cursor = user_data_collection.find_one(query, projection=projection)

        # Process
        if not cursor: points = 0
        else:          points = float(cursor['points'])

        if cursor: del cursor
        return points


    def get_user_rank(self, logger, db, user_id, db_type):
        user_data_collection = db(self.get_db(db_type, DB_ENUM.USER_DATA))

        # Request
        query      = { }
        projection = { 'points' : 1, 'user_id' : 1, 'user_name' : 1}
        cursor = user_data_collection.find(query, projection=projection)

        # Process
        if not cursor: rank = None
        else:          
            rank_list = sorted(cursor, key=lambda user_data: -float(user_data['points']))
            rank = [rank + 1 for rank in range(len(rank_list)) if str(rank_list[rank]['user_id']) == str(user_id)]
            rank = None if len(rank) == 0 else rank[0]

        if cursor: del cursor
        return rank


    def get_log_list(self, logger, db, db_type):
        '''
        'log_data' : [ 
            { 'time' : '...', 'user_name' : '...', 'user_id' : '...', 'post_id' : '...', 'added_score' : '...', 'total_score' : '...', },
            { 'time' : '...', 'user_name' : '...', 'user_id' : '...', 'post_id' : '...', 'added_score' : '...', 'total_score' : '...', },
            { 'time' : '...', 'user_name' : '...', 'user_id' : '...', 'post_id' : '...', 'added_score' : '...', 'total_score' : '...', },
            ... 
        ]
        '''
        log_data_collection = db(self.get_db(db_type, DB_ENUM.LOG_DATA))

        # Request
        query  = { 'log_data' : {'$exists' : True} }
        cursor = log_data_collection.find_one(query)

        # Process
        if not cursor: log_list = None
        else:          log_list = cursor['log_data']

        if cursor: del cursor
        return log_list


    def get_top_scores_list(self, logger, db, db_type):
        '''
        {
            { 'time' : '...', 'user_id' : '...', 'user_name' : '...', 'post_id' : '...', 'added_score' : '...' },
            { 'time' : '...', 'user_id' : '...', 'user_name' : '...', 'post_id' : '...', 'added_score' : '...' },
            ...
        }
        '''
        user_data_collection = db(self.get_db(db_type, DB_ENUM.TOP_SCORES))

        # Request
        query  = { 'top_scores_data' : {'$exists' : True} }
        cursor = user_data_collection.find_one(query)

        # Process
        if not cursor: top_scores_list = None
        else:          top_scores_list = cursor['top_scores_data']

        if cursor: del cursor
        return top_scores_list


    def get_top_10_list(self, logger, db, db_type):
        user_data_collection = db(self.get_db(db_type, DB_ENUM.USER_DATA))

        # Request
        query      = { }
        projection = { 'user_id' : 1, 'user_name' : 1, 'points' : 1 }
        cursor = user_data_collection.find(query, projection=projection).sort('points', pymongo.DESCENDING).limit(10)

        # Process
        if not cursor: top_10_list = [ ]
        else:          top_10_list = list(cursor)

        if cursor: del cursor
        return top_10_list


    def get_monthly_winners_list(self, logger, db):
        '''
        'monthly_winners' : [ 
            { 'time' : '...', 'user_id' : '...', 'points' : '...', 'user_name' : '...'},
            { 'time' : '...', 'user_id' : '...', 'points' : '...', 'user_name' : '...'},
            ...
        ]
        '''
        monthly_winners_data_collection = db(self.get_db(DB_ENUM.MONTHLY, DB_ENUM.MONTHLY_WINNERS))

        # Request
        query  = { 'monthly_winners' : {'$exists' : True} }
        cursor = monthly_winners_data_collection.find_one(query)

        # Process
        if not cursor: monthly_winners_list = []
        else:          monthly_winners_list = cursor['monthly_winners']

        if cursor: del cursor
        return monthly_winners_list


    def reset_monthly_data(self, logger, db):
        db(self.get_db(DB_ENUM.MONTHLY, DB_ENUM.USER_DATA)).delete_many({})
        db(self.get_db(DB_ENUM.MONTHLY, DB_ENUM.LOG_DATA)).delete_many({})
        db(self.get_db(DB_ENUM.MONTHLY, DB_ENUM.TOP_SCORES)).delete_many({})


    def generate_log_line(self, log_data, log_list):
        sign = '+' if float(log_data['added_score']) >= 0 else ''
        return self.generate_log_format(log_data, log_list).format(log_data['time'], log_data['user_name'], sign + str(log_data['added_score']), log_data['total_score'])


    def generate_log_format(self, log_data, log_list):
        longest_username = 0
        for log in log_list: longest_username = max(longest_username, len(log['user_name']))

        longest_score = 0
        for log in log_list: longest_score = max(longest_score, len(str(abs(float(log['added_score'])))))

        return '[ {0} ]    {1:<%d}  {2:<%d}  | Total Score: {3}' % (longest_username, longest_score + 1)

    
    def get_forum_log_text(self, logger, log_list):
        log_text = ''

        # Generate log lines
        for log_data in reversed(log_list[:]):
            log_text += self.generate_log_line(log_data, log_list) + '\n'

        if log_text == '': log_text = 'N/A'
        return log_text


    def get_top_scores_text(self, logger, top_scores_list):
        longest_username = 0
        for top_score in top_scores_list: longest_username = max(longest_username, len(top_score['user_name']))

        top_scores_format = '#{0:<%d} {1} {2:<%d}: {3} pts' % (2, longest_username)
        top_scores_text   = ''

        for i in range(len(top_scores_list)):
            text = top_scores_format.format(i+1, top_scores_list[i]['time'], top_scores_list[i]['user_name'] , top_scores_list[i]['added_score'])
            top_scores_text += text + '\n'

        if top_scores_text == '': top_scores_text = 'N/A'
        return top_scores_text


    def get_top_10_text(self, logger, db, top_10_list):
        longest_username = 0
        for user in top_10_list: longest_username = max(longest_username, len(user['user_name']))

        top_10_format = '#{0:<%d} {1:<%d}: {2} pts' % (2, longest_username)
        top_10_text   = ''

        for i in range(len(top_10_list)):
            text = top_10_format.format(i+1, top_10_list[i]['user_name'], top_10_list[i]['points'])
            top_10_text += text + '\n'

        if top_10_text == '': top_10_text = 'N/A'
        return top_10_text


    def get_monthly_winners_text(self, logger, monthly_winners_list):
        longest_username = 0
        for user in monthly_winners_list: longest_username = max(longest_username, len(user['user_name']))
            
        monthly_winners_format = '{0} {1:<%d}: {2} pts' % (longest_username)
        monthly_winners_text   = ''

        # Generate log lines
        for monthly_winner in monthly_winners_list[:]:
            monthly_winners_text += monthly_winners_format.format(monthly_winner['time'], monthly_winner['user_name'], monthly_winner['points']) + '\n'

        if monthly_winners_text == '': monthly_winners_text = 'N/A'
        return monthly_winners_text

    
    def get_prev_post_info(self, logger, db):
        log_data_collection = db(self.get_db(DB_ENUM.ALL_TIME, DB_ENUM.LOG_DATA))

        # Request
        query  = { 'log_data' : {'$exists' : True} }
        cursor = log_data_collection.find_one(query)

        # Process
        if not cursor: log_list = [ ]
        else:          log_list = cursor['log_data']

        if len(log_list) > 0: prev_post_info = log_list[-1]
        else:                 prev_post_info = None

        if cursor: del cursor
        return prev_post_info
