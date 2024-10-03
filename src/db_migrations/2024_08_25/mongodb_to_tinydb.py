"""
1. As root on server, package db files
    $ tar -cvf /home/server/Downloads/mongodb.tar.gz mongodb
2. As root on server, give read access to server
    $ chown root:server /home/server/Downloads/mongodb.tar.gz
3. On dev machine, transfer file from server
    > scp -P <port> -r server@<ip>:/home/server/Downloads/mongodb.tar.gz .
4. On dev machine, untar
5. On dev machine, run mongo
    > mongo --dbpath .\<path to untar>\mongo
6. On dev machine, run to dump to json
    > mongodump -d <database_name> -o <directory_backup>
7. On dev machine, run db migration
    > python src/db_migrations/2025_08_25/mongodb_to_tinydb.py <database_path> <output_path>
"""
import os
import sys
import json
import pathlib

import tinydb
import tinydb.table


sys.path.append(f'{os.getcwd()}')
sys.path.append(f'{os.getcwd()}\\src')

from src.core.ForumMonitor import ForumMonitor
from src.bots.ThreadNecroBot import ThreadNecroBot



def migrate_botcore(db_path: str, output: str):
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

    db_src = pathlib.Path(f'{db_path}/BotCore.json')
    db_dst = pathlib.Path(f'{output}/BotCore.json')
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


def migrate_bot_threadnecrobot_logdata(db_path: str, output: str):
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
            [type:int] : { 'num' : int },
        }
    """
    print('Processing threadnecrobot_logdata...')

    TABLE_LOG        = ThreadNecroBot._ThreadNecroBotCore__TABLE_LOGS
    TABLE_LOG_META   = ThreadNecroBot._ThreadNecroBotCore__TABLE_LOGS_META
    MAX_ENTRIES_LOGS = ThreadNecroBot._ThreadNecroBotCore__MAX_ENTRIES_LOGS

    data_out = {}

    db_dst = pathlib.Path(f'{output}/ThreadNecroBot_DataLogs.json')

    db_src = pathlib.Path(f'{db_path}/ThreadNecroBot_LogData.json')
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

    db_src = pathlib.Path(f'{db_path}/ThreadNecroBot_LogData_monthly.json')
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
        num = 0

        table = db.table(TABLE_LOG)
        for idx, entry in data_out.items():
            table.upsert(tinydb.table.Document(entry, idx))
            num = min(num + 1, MAX_ENTRIES_LOGS)

        table = db.table(TABLE_LOG_META)
        table.upsert(tinydb.table.Document({
            'num' : num
        }, 0))


def migrate_bot_threadnecrobot_winners(db_path: str, output: str):
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

    db_dst = pathlib.Path(f'{output}/ThreadNecroBot_DataWinners.json')

    db_src = pathlib.Path(f'{db_path}/ThreadNecroBot_MonthlyWinners.json')
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


def migrate_bot_threadnecrobot_topscores(db_path: str, output: str):
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

    db_dst = pathlib.Path(f'{output}/ThreadNecroBot_DataScores.json')

    db_src = pathlib.Path(f'{db_path}/ThreadNecroBot_TopScoresData.json')
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

    db_src = pathlib.Path(f'{db_path}/ThreadNecroBot_TopScoresData_monthly.json')
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


def migrate_bot_threadnecrobot_users(db_path: str, output: str):
    """
    in fmt DB:
        "userdata": [
            { "_id" : { "$oid" : str }, "points" : float, "post_id" : str, "user_id" : str, "user_name" : str},
            { "_id" : { "$oid" : str }, "points" : float, "post_id" : str, "user_id" : str, "user_name" : str},
            ...
        ]

    out fmt DB:
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
    print('Processing threadnecrobot_users...')
    TABLE_USERS_DATA    = ThreadNecroBot._ThreadNecroBotCore__TABLE_USERS_DATA
    TABLE_USERS_ALLTIME = ThreadNecroBot._ThreadNecroBotCore__TABLE_USERS_ALLTIME
    TABLE_USERS_MONTHLY = ThreadNecroBot._ThreadNecroBotCore__TABLE_USERS_MONTHLY

    data_out_data    = {}
    data_out_alltime = {}
    data_out_monthly = {}

    db_dst = pathlib.Path(f'{output}/ThreadNecroBot_DataUsers.json')

    db_src = pathlib.Path(f'{db_path}/ThreadNecroBot_UserData.json')
    with open(db_src) as f:
        data = json.load(f)

    # Go through old data and populate the new data
    for entry in data['userdata']:
        user_id = entry['user_id']
        if not user_id in data_out_data:    data_out_data[user_id]    = {}
        if not user_id in data_out_alltime: data_out_alltime[user_id] = {}
        if not user_id in data_out_monthly: data_out_monthly[user_id] = {}

        data_out_data[user_id].update({
            'user_name'      : str(entry['user_name']),
            'post_id'        : int(entry['post_id']),
        })
        data_out_alltime[user_id].update({
            'points' : float(entry['points']),
        })
        data_out_monthly[user_id].update({
            'points' : float(0),  # Default to 0
        })

    db_src = pathlib.Path(f'{db_path}/ThreadNecroBot_UserData_monthly.json')
    with open(db_src) as f:
        data = json.load(f)

    for entry in data['userdata']:
        user_id = entry['user_id']
        if not user_id in data_out_data:    data_out_data[user_id]    = {}
        if not user_id in data_out_monthly: data_out_monthly[user_id] = {}

        data_out_data[user_id].update({
            'user_name'      : str(entry['user_name']),
            'post_id'        : int(entry['post_id']),
        })
        data_out_monthly[user_id].update({
            'points' : float(entry['points']),
        })

    with tinydb.TinyDB(db_dst) as db:
        table = db.table(TABLE_USERS_DATA)
        for user_id, entry in data_out_data.items():
            table.upsert(tinydb.table.Document(entry, user_id))

        table = db.table(TABLE_USERS_ALLTIME)
        for user_id, entry in data_out_alltime.items():
            table.upsert(tinydb.table.Document(entry, user_id))

        table = db.table(TABLE_USERS_MONTHLY)
        for user_id, entry in data_out_monthly.items():
            table.upsert(tinydb.table.Document(entry, user_id))


def migrate_bot_threadnecrobot_metadata(db_path: str, output: str):
    """
    in fmt DB:
        "_id" : { "$oid" : str },
        "log_data" : [
            { "time" : str, "user_name" : str, "user_id" : str, "post_id" : str, "added_score" : str, "total_score" : str },
            { "time" : str, "user_name" : str, "user_id" : str, "post_id" : str, "added_score" : str, "total_score" : str },
            ...
        ]

    out fmt DB:
        "prevpost" : {
            [id:int] : { 'prev_post_id' : int, 'prev_post_time' : str, 'prev_post_user_id' : int },
            ...
        }
    """
    print('Processing threadnecrobot_metadata...')

    TABLE_META_PREV_POST = ThreadNecroBot._ThreadNecroBotCore__TABLE_META_PREV_POST

    db_dst = pathlib.Path(f'{output}/ThreadNecroBot_DataMeta.json')

    db_src = pathlib.Path(f'{db_path}/ThreadNecroBot_LogData.json')
    with open(db_src) as f:
        data = json.load(f)

    max_post_entry = max(data['log_data'], key=lambda x: int(x['post_id']))

    with tinydb.TinyDB(db_dst) as db:
        table_meta = db.table(TABLE_META_PREV_POST)
        table_meta.upsert(tinydb.table.Document({
            'prev_post_id'      : int(max_post_entry['post_id']),
            'prev_post_time'    : str(max_post_entry['time']),
            'prev_post_user_id' : int(max_post_entry['user_id']),
        }, doc_id=0))



if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <db_path> <output_path>')
        exit(1)

    db_path = sys.argv[1]
    output  = sys.argv[2]

    migrate_botcore(db_path, output)
    migrate_bot_threadnecrobot_logdata(db_path, output)
    migrate_bot_threadnecrobot_winners(db_path, output)
    migrate_bot_threadnecrobot_topscores(db_path, output)
    migrate_bot_threadnecrobot_users(db_path, output)
    migrate_bot_threadnecrobot_metadata(db_path, output)
