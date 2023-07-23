import tinydb
import config


db = tinydb.TinyDB('db-test.json')

def get_db(collection):
    return db.table(collection)


def check_db():
    print('Checking db...')
    forum_monitor_data = {
        'setting'          : 'ForumMonitor',
        'latest_post_id'   : config.latest_post_id,
        'avg_post_rate'    : 0,
    }

    table = get_db('forum-monitor')
    data = table.search(tinydb.where('setting') == 'ForumMonitor')

    if len(data) == 0:
        print('Database empty; Building new one...')
        table.insert(forum_monitor_data)


def retrieve_latest_post():
    table = get_db('forum-monitor')
    data = table.search(tinydb.where('setting') == 'ForumMonitor')
    
    if len(data) == 0:
        print('ForumMonitor settings not found!')
        return
    
    return int(data[0]['latest_post_id'])


def set_latest_post(post_id):
    table = get_db('forum-monitor')
    table.update({ 'latest_post_id': str(post_id) }, tinydb.where('setting') == 'ForumMonitor')


collection = get_db('forum-monitor')

check_db()

latest_post_id = retrieve_latest_post()
print(latest_post_id)
set_latest_post(1234356)
latest_post_id = retrieve_latest_post()
print(latest_post_id)
