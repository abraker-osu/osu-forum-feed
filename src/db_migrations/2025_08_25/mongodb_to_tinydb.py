import os
import sys
import json

import tinydb
import tinydb.table


sys.path.append(f'{os.getcwd()}')
sys.path.append(f'{os.getcwd()}\\src')

from src.core.ForumMonitor import ForumMonitor



def migrate_botcore():
    db_src = 'src\\db_migrations\\2025_08_25\\samples_in\\forum-bot.BotCore.json'
    db_dst = 'src\\db_migrations\\2025_08_25\\samples_out\\BotCore.json'
    with open(db_src) as f:
        data = json.load(f)

    with tinydb.TinyDB(db_dst) as db:
        table = db.table('Botcore')
        table.upsert(tinydb.table.Document(
            {
                'avg_post_rate'    : data['avg_post_rate'],
                'avg_thread_rate'  : data['avg_thread_rate'],
                'latest_post_id'   : data['latest_post_id'],
                'latest_thread_id' : data['latest_thread_id'],
                'setting'          : data['setting'],
            },
            ForumMonitor.DB_ID_FORUM_MONITOR
        ))


def migrate_bot_threadnecrobot_logdata():
    db_dst = 'src\\db_migrations\\2025_08_25\\samples_out\\ThreadNecroBot_LogData.json'

    db_src = 'src\\db_migrations\\2025_08_25\\samples_in\\forum-bot.ThreadNecroBot_LogData.json'
    with open(db_src) as f:
        data = json.load(f)

    with tinydb.TinyDB(db_dst) as db:
        table = db.table('log_data')
        for i, entry in enumerate(data['log_data']):
            table.upsert(tinydb.table.Document(entry, i))

    db_src = 'src\\db_migrations\\2025_08_25\\samples_in\\forum-bot.ThreadNecroBot_LogData_monthly.json'
    with open(db_src) as f:
        data = json.load(f)

    with tinydb.TinyDB(db_dst) as db:
        table = db.table('log_data_monthly')
        for i, entry in enumerate(data['log_data']):
            table.upsert(tinydb.table.Document(entry, i))


def migrate_bot_threadnecrobot_winners():
    db_dst = 'src\\db_migrations\\2025_08_25\\samples_out\\ThreadNecroBot_MonthlyWinners.json'

    db_src = 'src\\db_migrations\\2025_08_25\\samples_in\\forum-bot.ThreadNecroBot_MonthlyWinners.json'
    with open(db_src) as f:
        data = json.load(f)

    with tinydb.TinyDB(db_dst) as db:
        table = db.table('monthly_winners')
        for i, entry in enumerate(data['monthly_winners']):
            del entry['_id']
            table.upsert(tinydb.table.Document(entry, i))


def migrate_bot_threadnecrobot_topscores():
    db_dst = 'src\\db_migrations\\2025_08_25\\samples_out\\ThreadNecroBot_TopScoresData.json'

    db_src = 'src\\db_migrations\\2025_08_25\\samples_in\\forum-bot.ThreadNecroBot_TopScoresData.json'
    with open(db_src) as f:
        data = json.load(f)

    with tinydb.TinyDB(db_dst) as db:
        table = db.table('top_scores')
        for i, entry in enumerate(data['top_scores_data']):
            table.upsert(tinydb.table.Document(entry, i))

    db_src = 'src\\db_migrations\\2025_08_25\\samples_in\\forum-bot.ThreadNecroBot_TopScoresData_monthly.json'
    with open(db_src) as f:
        data = json.load(f)

    with tinydb.TinyDB(db_dst) as db:
        table = db.table('top_scores_monthly')
        for i, entry in enumerate(data['top_scores_data']):
            table.upsert(tinydb.table.Document(entry, i))


def migrate_bot_threadnecrobot_users():
    db_dst = 'src\\db_migrations\\2025_08_25\\samples_out\\ThreadNecroBot_UserData.json'

    db_src = 'src\\db_migrations\\2025_08_25\\samples_in\\forum-bot.ThreadNecroBot_UserData.json'
    with open(db_src) as f:
        data = json.load(f)

    with tinydb.TinyDB(db_dst) as db:
        table = db.table('userdata')
        for entry in data['userdata']:
            user_id = entry['user_id']
            del entry['_id']
            del entry['user_id']
            table.upsert(tinydb.table.Document(entry, user_id))

    db_src = 'src\\db_migrations\\2025_08_25\\samples_in\\forum-bot.ThreadNecroBot_UserData_monthly.json'
    with open(db_src) as f:
        data = json.load(f)

    with tinydb.TinyDB(db_dst) as db:
        table = db.table('userdata_monthly')
        for entry in data['userdata']:
            user_id = entry['user_id']
            del entry['_id']
            del entry['user_id']
            table.upsert(tinydb.table.Document(entry, user_id))



migrate_botcore()
migrate_bot_threadnecrobot_logdata()
migrate_bot_threadnecrobot_winners()
migrate_bot_threadnecrobot_topscores()
migrate_bot_threadnecrobot_users()
