"""
Run mongodb

> mongoexport --db local --collection system.indexes --out .\converted_json\local.system.indexes.json
"""
import os
import sys
import json

import tinydb
import tinydb.table


sys.path.append(f'{os.getcwd()}')
sys.path.append(f'{os.getcwd()}\\src')

from src.core.ForumMonitor import ForumMonitor
from src.bots.ThreadNecroBot import ThreadNecroBot



def migrate_botcore():
    """
    in fmt DB:
        {
            "_id" : { "$oid" : str },
            "avg_post_rate"    : str,
            "avg_thread_rate"  : str,
            "latest_post_id"   : str,
            "latest_thread_id" : str",
            "setting"          : "ForumMonitor"
        }

    out fmt DB:
        "Botcore": {
            "0": {
                "avg_post_rate"    : int,
                "avg_thread_rate"  : int,
                "latest_post_id"   : int,
                "latest_thread_id" : int,
                "setting"          : "ForumMonitor"
            }
        }

    """
    print('Processing botcore...')

    TABLE_BOTCORE    = ForumMonitor._ForumMonitor__TABLE_BOTCORE
    ID_FORUM_MONITOR = ForumMonitor._ForumMonitor__DB_ID_FORUM_MONITOR

    db_src = 'src\\db_migrations\\2025_08_25\\samples_in\\forum-bot.BotCore.json'
    db_dst = 'src\\db_migrations\\2025_08_25\\samples_out\\BotCore.json'
    with open(db_src) as f:
        data = json.load(f)

    with tinydb.TinyDB(db_dst) as db:
        table = db.table(TABLE_BOTCORE)
        table.upsert(tinydb.table.Document(
            {
                'avg_post_rate'    : int(data['avg_post_rate']),
                'avg_thread_rate'  : int(data['avg_thread_rate']),
                'latest_post_id'   : int(data['latest_post_id']),
                'latest_thread_id' : int(data['latest_thread_id']),
                'setting'          : str(data['setting']),
            },
            ID_FORUM_MONITOR
        ))


def migrate_bot_threadnecrobot_logdata():
    """
    in fmt DB:
        "_id" : { "$oid" : str },
        "log_data" : [
            { "time" : str, "user_name" : str, "user_id" : str, "post_id" : str, "added_score" : str, "total_score" : str },
            { "time" : str, "user_name" : str, "user_id" : str, "post_id" : str, "added_score" : str, "total_score" : str },
            ...
        ]

    out fmt DB:
        "log_data" : {
            [idx:int] : { 'time' : str, 'user_name' : str, 'user_id' : int, 'post_id' : int, 'added_score' : float, 'score_alltime' : float, 'score_monthly' : float },
            [idx:int] : { 'time' : str, 'user_name' : str, 'user_id' : int, 'post_id' : int, 'added_score' : float, 'score_alltime' : float, 'score_monthly' : float },
            ...
        },
        "log_data_meta : {
            [type:int] : { 'idx' : int },
        }
    """
    print('Processing threadnecrobot_logdata...')

    TABLE_LOG        = ThreadNecroBot._ThreadNecroBotCore__TABLE_LOGS
    TABLE_LOG_META   = ThreadNecroBot._ThreadNecroBotCore__TABLE_LOGS_META
    MAX_ENTRIES_LOGS = ThreadNecroBot._ThreadNecroBotCore__MAX_ENTRIES_LOGS

    data_out = {}

    db_dst = 'src\\db_migrations\\2025_08_25\\samples_out\\ThreadNecroBot_DataLogs.json'

    db_src = 'src\\db_migrations\\2025_08_25\\samples_in\\forum-bot.ThreadNecroBot_LogData.json'
    with open(db_src) as f:
        data = json.load(f)

    for idx, entry in enumerate(data['log_data']):
        if not idx in data_out:
            data_out[idx] = {}

        data_out[idx].update({
            'time'          : str(entry['time']),
            'user_name'     : str(entry['user_name']),
            'user_id'       : int(entry['user_id']),
            'post_id'       : int(entry['post_id']),
            'added_score'   : float(entry['added_score']),
            'score_alltime' : float(entry['total_score']),
        })

    db_src = 'src\\db_migrations\\2025_08_25\\samples_in\\forum-bot.ThreadNecroBot_LogData_monthly.json'
    with open(db_src) as f:
        data = json.load(f)

    for idx, entry in enumerate(data['log_data']):
        if not idx in data_out:
            data_out[idx] = {}

        data_out[idx].update({
            'time'          : str(entry['time']),
            'user_name'     : str(entry['user_name']),
            'user_id'       : int(entry['user_id']),
            'post_id'       : int(entry['post_id']),
            'added_score'   : float(entry['added_score']),
            'score_monthly' : float(entry['total_score']),
        })

    with tinydb.TinyDB(db_dst) as db:
        log_idx = 0

        table = db.table(TABLE_LOG)
        for idx, entry in data_out.items():
            table.upsert(tinydb.table.Document(entry, idx))

            # Keep track of log idx, and wrap it around to max log entries
            log_idx += 1
            if log_idx >= MAX_ENTRIES_LOGS:
                log_idx = 0

        table = db.table(TABLE_LOG_META)
        table.upsert(tinydb.table.Document({
            'idx' : log_idx
        }, 0))


def migrate_bot_threadnecrobot_winners():
    """
    in fmt DB:
        "_id" : { "$oid" : str },
        "monthly_winners" : [
            { "_id" : { "$oid" : str }, "points" : float, "user_id" : str, "user_name" : str, "time": str },
            { "_id" : { "$oid" : str }, "points" : float, "user_id" : str, "user_name" : str, "time": str },
            ...
        ]

    out fmt DB:
        'monthly_winners' : {
            [idx:int] : { 'time' : str, 'user_id' : int, 'points' : float, 'user_name' : str },
            [idx:int] : { 'time' : str, 'user_id' : int, 'points' : float, 'user_name' : str },
            ...
        }
    """
    print('Processing threadnecrobot_winners...')

    TABLE_WINNERS = ThreadNecroBot._ThreadNecroBotCore__TABLE_WINNERS

    db_dst = 'src\\db_migrations\\2025_08_25\\samples_out\\ThreadNecroBot_DataWinners.json'

    db_src = 'src\\db_migrations\\2025_08_25\\samples_in\\forum-bot.ThreadNecroBot_MonthlyWinners.json'
    with open(db_src) as f:
        data = json.load(f)

    with tinydb.TinyDB(db_dst) as db:
        table = db.table(TABLE_WINNERS)
        for i, entry in enumerate(data['monthly_winners']):
            table.upsert(tinydb.table.Document({
                'time'      : str(entry['time']),
                'user_id'   : int(entry['user_id']),
                'points'    : float(entry['points']),
                'user_name' : str(entry['user_name'])
            }, i))


def migrate_bot_threadnecrobot_topscores():
    """
    in fmt DB:
        "_id" : { "$oid" : str },
        "top_scores_data" : [
            { "time" : str, "user_id" : str, "user_name" : str, "post_id" : str, "added_score" : str },
            { "time" : str, "user_id" : str, "user_name" : str, "post_id" : str, "added_score" : str },
            ...
        ]

    out fmt DB:
        "top_scores", "top_scores_monthly" : {
            [idx:int] : { 'time' : str, 'user_id' : int, 'user_name' : str, 'post_id' : int, 'added_score' : float },
            [idx:int] : { 'time' : str, 'user_id' : int, 'user_name' : str, 'post_id' : int, 'added_score' : float },
            ...
        }
    """
    print('Processing threadnecrobot_topscores...')

    TABLE_SCORES_ALLTIME  = ThreadNecroBot._ThreadNecroBotCore__TABLE_SCORES_ALLTIME
    TABLE_SCORES_MONTHLY  = ThreadNecroBot._ThreadNecroBotCore__TABLE_SCORES_MONTHLY

    db_dst = 'src\\db_migrations\\2025_08_25\\samples_out\\ThreadNecroBot_DataScores.json'

    db_src = 'src\\db_migrations\\2025_08_25\\samples_in\\forum-bot.ThreadNecroBot_TopScoresData.json'
    with open(db_src) as f:
        data = json.load(f)

    with tinydb.TinyDB(db_dst) as db:
        table = db.table(TABLE_SCORES_ALLTIME)
        for i, entry in enumerate(data['top_scores_data']):
            table.upsert(tinydb.table.Document({
                'time'        : str(entry['time']),
                'user_id'     : int(entry['user_id']),
                'user_name'   : str(entry['user_name']),
                'post_id'     : int(entry['post_id']),
                'added_score' : float(entry['added_score']),
            }, i))

    db_src = 'src\\db_migrations\\2025_08_25\\samples_in\\forum-bot.ThreadNecroBot_TopScoresData_monthly.json'
    with open(db_src) as f:
        data = json.load(f)

    with tinydb.TinyDB(db_dst) as db:
        table = db.table(TABLE_SCORES_MONTHLY)
        for i, entry in enumerate(data['top_scores_data']):
            table.upsert(tinydb.table.Document({
                'time'        : str(entry['time']),
                'user_id'     : int(entry['user_id']),
                'user_name'   : str(entry['user_name']),
                'post_id'     : int(entry['post_id']),
                'added_score' : float(entry['added_score']),
            }, i))


def migrate_bot_threadnecrobot_users():
    """
    in fmt DB:
        "userdata": [
            { "_id" : { "$oid" : str }, "points" : float, "post_id" : str, "user_id" : str, "user_name" : str},
            { "_id" : { "$oid" : str }, "points" : float, "post_id" : str, "user_id" : str, "user_name" : str},
            ...
        ]

    out fmt DB:
        "userdata" : {
            [user_id:int] : { 'points_alltime' : float, 'points_monthly' : float, 'user_name' : str, 'post_id' : int },
            [user_id:int] : { 'points_alltime' : float, 'points_monthly' : float, 'user_name' : str, 'post_id' : int },
            ...
        }
    """
    print('Processing threadnecrobot_users...')

    data_out = {}

    db_dst = 'src\\db_migrations\\2025_08_25\\samples_out\\ThreadNecroBot_DataUsers.json'

    db_src = 'src\\db_migrations\\2025_08_25\\samples_in\\forum-bot.ThreadNecroBot_UserData.json'
    with open(db_src) as f:
        data = json.load(f)

    for entry in data['userdata']:
        user_id = entry['user_id']
        if not entry['user_id'] in data_out:
            data_out[user_id] = {}

        data_out[user_id].update({
            'user_name'      : str(entry['user_name']),
            'points_alltime' : float(entry['points']),
            'post_id'        : int(entry['post_id'])
        })

    db_src = 'src\\db_migrations\\2025_08_25\\samples_in\\forum-bot.ThreadNecroBot_UserData_monthly.json'
    with open(db_src) as f:
        data = json.load(f)

    for entry in data['userdata']:
        user_id = entry['user_id']
        if not entry['user_id'] in data_out:
            data_out[user_id] = {}

        data_out[user_id].update({
            'user_name'      : str(entry['user_name']),
            'points_monthly' : float(entry['points']),
            'post_id'        : int(entry['post_id'])
        })

    with tinydb.TinyDB(db_dst) as db:
        table = db.table('userdata')
        for user_id, entry in data_out.items():
            table.upsert(tinydb.table.Document(entry, user_id))



migrate_botcore()
migrate_bot_threadnecrobot_logdata()
migrate_bot_threadnecrobot_winners()
migrate_bot_threadnecrobot_topscores()
migrate_bot_threadnecrobot_users()
