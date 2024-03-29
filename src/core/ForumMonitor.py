from typing import Optional, Union

import time
import logging
import requests

import tinydb
from tinydb.table import Document

from threading import Thread

from core.BotCore import BotCore
from core.SessionMgr import SessionMgr
from core import BotException


class ForumMonitor(BotCore, SessionMgr):

    DB_ID_FORUM_MONITOR = 0

    NEW_POST = 1

    def __init__(self, config: dict, login: bool = True):
        self.__logger = logging.getLogger(__class__.__name__)
        self.__logger.info('ForumMonitor initializing...')

        BotCore.__init__(self, config)
        SessionMgr.__init__(self)

        if login:
            self.login(self.get_cfg('Core', 'web_username'), self.get_cfg('Core', 'web_password'))

        self.__post_rate = 5.0

        self.__latest_post_id = None
        self.__latest_post_id = self.__retrieve_latest_post()
        self.__check_post_ids = [ self.__latest_post_id ]

        self.__logger.info(f'latest_post_id: {self.__latest_post_id}')

        # Is the following monitor enabled?
        self.__monitor_enables = {
            ForumMonitor.NEW_POST : True,
        }

        # Is the following monitor undergoing operation?
        self.__monitor_statuses = {
            ForumMonitor.NEW_POST : False,
        }


    def __del__(self):
        BotCore.__del__(self)


    def check_db(self):
        """
        db format:
        {
             "0": { "latest_post_id": (post_id: int) }
        }
        """
        self.__logger.info('Checking db...')
        table = BotCore.get_db_table(self, 'BotCore')

        entry = table.get(doc_id=ForumMonitor.DB_ID_FORUM_MONITOR)
        if not isinstance(entry, type(None)):
            # Check for the `latest_post_id` field
            if not 'latest_post_id' in entry:
                self.__logger.warning('Forum monitor table exists but `latest_post_id` does not!')
                # TODO: Fill it in?

            self.__logger.info('db ok')
            return

        self.__logger.info('Forum monitor db empty; Building new one...')
        table.insert(Document(
            {
                'latest_post_id' : self.get_cfg('Core', 'latest_post_id'),
            },
            ForumMonitor.DB_ID_FORUM_MONITOR
        ))


    def get_latest_post(self) -> int:
        if not self.__latest_post_id:
            self.__logger.debug('Latest post id is not set; retrieving from db...')
            return self.__retrieve_latest_post()

        return self.__latest_post_id


    def __retrieve_latest_post(self) -> int:
        """
        db format:
        {
             "0": { "latest_post_id": (post_id: int) }
        }
        """
        table = self.get_db_table('BotCore')

        entry = table.get(doc_id=ForumMonitor.DB_ID_FORUM_MONITOR)
        if isinstance(entry, type(None)):
            # This should not happen as the db was checked
            # So db may have unexpectedly modified by external means between then and now
            raise Exception('ForumMonitor settings not found!')

        self.__logger.debug(f'FETCH latest_post id: {entry["latest_post_id"]}')
        return int(entry['latest_post_id'])


    def set_latest_post(self, post_id: int):
        """
        db format:
        {
             "0": { "latest_post_id": (post_id: int) }
        }
        """
        table = self.get_db_table('BotCore')
        table.upsert(Document(
            {
                'latest_post_id' : post_id
            },
            ForumMonitor.DB_ID_FORUM_MONITOR
        ))

        self.__latest_post_id = post_id
        self.__check_post_ids = [ post_id ]

        self.__logger.debug(f'SET latest_post_id: {post_id}')


    def get_enable(self, event_type: int):
        if not event_type in self.__monitor_enables:
            msg = f'Invalid event type {event_type}'
            self.__logger.debug(msg)
            raise BotException(self.__logger, msg)

        return self.__monitor_enables[event_type]


    def set_enable(self, event_type: int, enable: bool):
        if not event_type in self.__monitor_enables:
            msg = f'Invalid event type {event_type}'
            self.__logger.debug(msg)
            raise BotException(self.__logger, msg)

        self.__logger.info(f'Setting event type {event_type} to {enable}')
        self.__monitor_enables[event_type] = enable


    def get_status(self, event_type: int):
        if not event_type in self.__monitor_statuses:
            msg = f'Invalid event type {event_type}'
            self.__logger.debug(msg)
            raise BotException(self.__logger, msg)

        return self.__monitor_statuses[event_type]


    def __set_status(self, event_type: int, status: bool):
        if not event_type in self.__monitor_statuses:
            msg = f'Invalid event type {event_type}'
            self.__logger.debug(msg)
            raise BotException(self.__logger, msg)

        self.__monitor_statuses[event_type] = status


    def fetch_post(self, check_post_id: Union[int, str]) -> "tuple[Optional[str], Optional[requests.Response]]":
        # Request website data
        post_url = f'https://osu.ppy.sh/community/forums/posts/{check_post_id}'
        self.__logger.debug(f'Checking post id: {check_post_id}')

        # Try to get web data. If we can't due to server error, then abort and retry after some time
        try: page = self.fetch_web_data(post_url)
        except BotException:
            return None, None

        return post_url, page


    def run(self):
        new_post_task   = None
        last_post_check = time.time()

        warned_post_check_timeout = False
        timeout = 60*5   # 5 minutes

        # Due to the checking if the task is running, there will never be more than two new_thread_task or new_post_task
        # running at the same time. This means that bots will process one thread or post at a time
        # \FIXME: Sudden internet disconnect creates cascade errors across everything. Need to keep on retrying
        # \TODO: See if basing the speed on how far back the threads are will work. Would be a function of time between now and the read thread/post
        while True:
            try:
                time.sleep(1)  # sleep for 1 second
                if self.runtime_quit:
                    break

                if self.get_enable(ForumMonitor.NEW_POST) == True:
                    if not warned_post_check_timeout:
                        if time.time() - last_post_check > timeout:
                            self.__logger.warn('Post checking has timed out! (this means one of the modules halted)')
                            warned_post_check_timeout = True

                if not new_post_task or not new_post_task.isAlive():
                    self.__set_status(ForumMonitor.NEW_POST, False)
                    if self.get_enable(ForumMonitor.NEW_POST) == True:
                        new_post_task = Thread(target=self.__check_new_post, args=[])
                        new_post_task.start()

                        last_post_check = time.time()
                        self.__set_status(ForumMonitor.NEW_POST, True)

            except KeyboardInterrupt:
                self.__logger.info(f'Exiting main loop.')
                self.runtime_quit = True
            except Exception as e:
                self.__logger.exception(f'Exception in main loop!')
                raise e

        if new_post_task:
            new_post_task.join()


    def __check_new_post(self):
        check_post_ids = self.__check_post_ids[:]
        for i in range(len(check_post_ids)):
            if self.runtime_quit:
                return

            try:
                time.sleep(self.__post_rate)

                post_url, page = self.fetch_post(check_post_ids[i])
                if isinstance(page, type(None)):
                    continue

                # Ok post
                if page.status_code == 200:
                    self.handle_new_post(check_post_ids, i, page)
                    return
            except BotException as e:
                self.__logger.error(f'{e}\nPost id {check_post_ids[i]}'); break
            except RuntimeError as e:
                self.__logger.error(f'{e}\nPost id {check_post_ids[i]}'); break
            except KeyboardInterrupt:
                self.runtime_quit = True; break
            except Exception as e:
                self.__logger.exception(f'{e}\nPost id {check_post_ids[i]}'); break

            self.__logger.debug(f'Post ID: {check_post_ids[i]}    Status: {page.status_code}')

            # Too many requests -> start over
            if page.status_code == 429:
                if self.__post_rate < self.get_cfg('Core', 'rate_post_max'):
                    self.__post_rate += 0.1
                    if self.__post_rate >= self.get_cfg('Core', 'rate_post_warn'):
                        self.__logger.warning('Forum monitor post rate has reached over 5 sec!')
                return

            # Post not found/available -> add next id and start over
            if (check_post_ids[-1] + 1) not in self.__check_post_ids:
                self.__check_post_ids.append(check_post_ids[-1] + 1)


    def handle_new_post(self, check_post_ids: "list[int]", i: int, page: requests.Response):
        # Recheck the posts in the list before this one
        for j in range(i):
            if self.runtime_quit:
                return

            time.sleep(self.__post_rate)

            # Silent re-look over
            # tmp so not to overwite the post_url and page we have for the found post
            try: post_url_tmp, page_tmp = self.fetch_post(check_post_ids[j])
            except:
                continue

            if isinstance(page_tmp, type(None)) or (page_tmp.status_code != 200):
                continue

            # If we found an earlier post, make that the latest post
            if page_tmp.status_code == 200:
                page = page_tmp
                i = j
                break

        # Lower rate since there is a successful request
        self.__post_rate = max(self.get_cfg('Core', 'rate_post_min'), self.__post_rate - 0.1)

        # That is our latest post id and no need to check for any other but the next one
        self.set_latest_post(check_post_ids[i] + 1)
        post = self.get_post(check_post_ids[i], page)

        self.__logger.debug(f'Latest post ID: {check_post_ids[i]}\tDate: {post.date}')

        # Send off the post data to the bots
        self.forum_driver(post)
