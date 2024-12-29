from typing import Optional

import time
import logging
import requests
import warnings
import threading
import queue

import tinydb
from tinydb import table

from misc.thread_enchanced import ThreadEnchanced
from misc.threaded_obj import Threaded

from .BotConfig import BotConfig
from .BotCore import BotCore
from .SessionMgrV2 import SessionMgrV2
from .BotException import BotException
from .DiscordClient import DiscordClient



class ForumMonitor(BotCore):

    NEW_POST = 1

    __DB_FILE_BOTCORE     = 'BotCore.json'
    __DB_TABLE_BOTCORE    = 'Botcore'
    __DB_ID_FORUM_MONITOR = 0

    __instance = None

    def __new__(cls):
        """
        Singleton
        """
        if not cls.__instance:
            cls.__instance = super().__new__(cls)

        return cls.__instance


    def __init__(self):
        self.__logger = logging.getLogger(__class__.__name__)

        try:
            DiscordClient.request('admin/post', {
                'src' : 'forumbot',
                'contents' : f'```Forum monitor starting...```'
            })
        except Exception as e:
            warnings.warn(f'Unable to send message to Discord: {e}')

        BotCore.__init__(self)
        SessionMgrV2.login()

        self.__post_rate      = Threaded(5.0)
        self.__latest_post_id = Threaded(self.__retrieve_latest_post())
        self.__check_post_ids = Threaded([ self.__latest_post_id.get() ])

        self.__thread_check_post_loop = ThreadEnchanced(
            target=self.__check_posts_loop, args=( threading.Event(), threading.Event() ),
            daemon=True
        )
        self.__thread_new_post_loop = ThreadEnchanced(
            target=self.__handle_posts_loop, args=( threading.Event(), threading.Event() ),
            daemon=True
        )
        self.__post_queue = queue.Queue()

        self.__logger.info(f'latest_post_id: {self.__latest_post_id}')

        # Is the following monitor enabled?
        self.__monitor_enables = {
            ForumMonitor.NEW_POST : True,
        }


    def check_db(self):
        """
        Overrides `BotCore.check_db`

        fmt DB:
            {
                "0": {
                    "avg_post_rate"    : int,
                    "avg_thread_rate"  : int,
                    "latest_post_id"   : int,
                    "latest_thread_id" : int,
                }
            }
        """
        self.__logger.info(f'Checking db at {self._db_path}/{self.__DB_FILE_BOTCORE}...')

        with tinydb.TinyDB(f'{self._db_path}/{self.__DB_FILE_BOTCORE}') as db:
            table_botcore = db.table(self.__DB_TABLE_BOTCORE)

            entry = table_botcore.get(doc_id=self.__DB_ID_FORUM_MONITOR)
            if not isinstance(entry, type(None)):
                # Check for the `latest_post_id` field
                if not 'latest_post_id' in entry:
                    self.set_latest_post(BotConfig['Core']['latest_post_id'])

                self.__logger.info('db ok')
                return

            # [2024.09.25] TODO: Check other fields?

            self.__logger.info('Forum monitor db empty; Building new one...')
            table_botcore.insert(table.Document(
                {
                    # [2024.09.25] TODO: Add stat fields
                    'latest_post_id' : BotConfig['Core']['latest_post_id'],
                },
                ForumMonitor.__DB_ID_FORUM_MONITOR
            ))


    def get_latest_post(self) -> int:
        """
        Retrieves the latest post id from db or from memory if already set.

        Returns
        -------
        int
            The latest post id.
        """
        latest_post_id = self.__latest_post_id.get()
        if not latest_post_id:
            self.__logger.debug('Latest post id is not set; retrieving from db...')
            return self.__retrieve_latest_post()

        return latest_post_id


    def __retrieve_latest_post(self) -> int:
        """
        fmt DB:
            {
                "0": {
                    "avg_post_rate"    : int,
                    "avg_thread_rate"  : int,
                    "latest_post_id"   : int,
                    "latest_thread_id" : int,
                }
            }
        """
        with tinydb.TinyDB(f'{self._db_path}/{self.__DB_FILE_BOTCORE}') as db:
            table_botcore = db.table(self.__DB_TABLE_BOTCORE)

            entry = table_botcore.get(doc_id=self.__DB_ID_FORUM_MONITOR)
            if not isinstance(entry, table.Document):
                # This should not happen as the db was checked
                # So db may have unexpectedly modified by external means between then and now
                raise BotException('ForumMonitor settings not found!')

            self.__logger.debug(f'FETCH latest_post id: {entry["latest_post_id"]}')
            return int(entry['latest_post_id'])


    def set_latest_post(self, post_id: int):
        """
        Sets the latest post id in the db and memory.

        fmt DB:
            {
                "0": { "latest_post_id": (post_id: int) }
            }

        Parameters
        ----------
        post_id : int
            The id of the post to set the latest post id to.
        """
        with tinydb.TinyDB(f'{self._db_path}/{self.__DB_FILE_BOTCORE}') as db:
            table_botcore = db.table(self.__DB_TABLE_BOTCORE)
            table_botcore.upsert(table.Document(
                {
                    'latest_post_id' : post_id
                },
                self.__DB_ID_FORUM_MONITOR
            ))

        self.__latest_post_id.set(post_id)
        self.__check_post_ids.set([ post_id ])

        self.__logger.debug(f'SET latest_post_id: {post_id}')


    def fetch_post(self, post_id: int | str) -> tuple[Optional[str], Optional[requests.Response]]:
        post_url = f'https://osu.ppy.sh/community/forums/posts/{post_id}'
        self.__logger.debug(f'Fetching post id: {post_id}')

        # Try to get web data. If not possible due to server error, then abort and retry after some time
        try: page = SessionMgrV2.fetch_web_data(post_url)
        except BotException:
            return None, None

        return post_url, page


    def run(self):
        self.__logger.info('Starting forum monitor...')
        self.__thread_check_post_loop.start()
        self.__thread_new_post_loop.start()

        # Due to the checking if the task is running, the bots will process one post at a time.
        # This is desired as a preventive measure against hitting osu!web rate limits.
        while not self.runtime_quit:
            try:
                time.sleep(1)

                # TODO: Get these loops running again instead of restarting the bot
                if not self.__thread_check_post_loop.is_alive():
                    warnings.warn(f'Post checking loop is dead!')
                    self.runtime_quit = True

                if not self.__thread_new_post_loop.is_alive():
                    warnings.warn(f'Post processing loop is dead!')
                    self.runtime_quit = True

            except KeyboardInterrupt:
                self.__logger.info(f'Exiting main loop.')
                self.runtime_quit = True
            except Exception as e:
                self.__logger.error(f'Exception in forum monitor loop: {e}')
                try: raise BotException(f'Exception in forum monitor loop: {e}') from e
                except:
                    pass

        self.__thread_check_post_loop.stop()
        self.__thread_check_post_loop.join()

        self.__thread_new_post_loop.stop()
        self.__thread_new_post_loop.join()


    def __check_posts(self, check_post_ids: list[int]) -> tuple[int, requests.Response | None]:
        rate_post_max  = BotConfig['Core']['rate_post_max']
        rate_post_min  = BotConfig['Core']['rate_post_min']
        rate_gracetime = BotConfig['Core']['rate_gracetime']

        last_rate_limit = 0

        self.__logger.debug(f'Starting post check run for: {check_post_ids}')

        i = 0
        while i < len(check_post_ids):
            time.sleep(self.__post_rate.get())

            post_url, page = self.fetch_post(check_post_ids[i])
            if isinstance(page, type(None)):
                warnings.warn(f'Failed to fetch post {check_post_ids[i]}: Page is None')
                continue

            self.__logger.debug(f'Checking post id: {check_post_ids[i]}    Status: {page.status_code}   Post rate: {self.__post_rate}')

            # Too many requests -> start over
            if page.status_code == 429:
                last_rate_limit = time.time()
                self.__post_rate.set(min(rate_post_max, self.__post_rate + 0.1))
                continue

            # Ok post
            if page.status_code == 200:
                # If some time has passed since the last rate limit, reduce the post rate
                rate_limit_period = time.time() - last_rate_limit
                if rate_limit_period > rate_gracetime * self.__post_rate:
                    # Lower rate since there is a successful request
                    self.__post_rate.set(max(rate_post_min, self.__post_rate - 0.1))

                self.__logger.debug(f'Found new post ID: {check_post_ids[i]}')
                return check_post_ids[i], page

            i += 1

        # Post not found/available -> add next id and start over
        self.__logger.debug(f'No new posts found: {check_post_ids}')
        return -1, None


    def __check_posts_loop(self, thread_event: threading.Event, target_event: threading.Event):
        rate_post_warn = BotConfig['Core']['rate_post_warn']

        warned = False

        while True:
            target_event.set()

            if thread_event.is_set():
                self.__logger.debug(f'Got stop signal for thread {threading.current_thread().name}')
                target_event.set()
                return

            check_post_ids = self.__check_post_ids.get().copy()

            try:
                # Check for new posts
                post_id0, page0 = self.__check_posts(check_post_ids)
                if isinstance(page0, type(None)) and post_id0 == -1:
                    if (check_post_ids[-1] + 1) not in self.__check_post_ids.get():
                        self.__check_post_ids.append(check_post_ids[-1] + 1)
                    continue

                assert isinstance(page0, requests.Response) and post_id0 > 0

                # re-look over prev ids to make sure a previous one that was not available wasnt missed
                post_id1, page1 = self.__check_posts(list(range(check_post_ids[0], post_id0)))
                if isinstance(page1, requests.Response) and post_id1 > 0:
                    page    = page1
                    post_id = post_id1
                else:
                    page    = page0
                    post_id = post_id0

                # That is our latest post id and no need to check for any other but the next one
                self.set_latest_post(post_id + 1)
                assert len(self.__check_post_ids.get()) == 1

                # Send post to forum bots
                self.__logger.debug(f'Queuing post id: {post_id}')
                self.__post_queue.put( ( post_id, page ) )

                # Process warnings for post rate
                if not warned and self.__post_rate >= rate_post_warn:
                    warnings.warn('```Forum monitor post rate has reached over 5 sec!```', UserWarning, source='forumbot')
                    warned = True

                if warned and self.__post_rate < rate_post_warn:
                    warned = False

            except KeyboardInterrupt:
                self.runtime_quit = True
            except Exception as e:
                self.__logger.error(f'Exception in post check loop: {e}')
                try: raise BotException(f'Exception in post check loop: {e}') from e
                except:
                    pass


    def __handle_posts_loop(self, thread_event: threading.Event, target_event: threading.Event):
        target_event.set()

        while True:
            if thread_event.is_set():
                while not self.__post_queue.empty():
                    self.__post_queue.get()

                self.__logger.debug(f'Got stop signal for thread {threading.current_thread().name}')
                target_event.set()
                return

            try: data: tuple[int, requests.Response] = self.__post_queue.get(block=True, timeout=1)
            except queue.Empty:
                continue

            post_id, page = data

            try:
                post = SessionMgrV2.get_post(post_id, page)
                self.__logger.debug(f'Processing post ID: {post_id} | date: {post.date} | subforum: {post.topic.subforum_name}')

                # Send off the post data to the bots
                self.forum_driver(post)
            except Exception as e:
                self.__logger.error(f'Error handling new post: {e}')
                try: raise BotException(f'Warning: {e}') from e
                except:
                    pass


# NOTE: For this to work for the bots it must be imported
#   from within the functions that depends on this. Otherwise,
#   if the imported from top of file, the import chain will
#   run before this assignment is reached.
ForumMonitor = ForumMonitor()
