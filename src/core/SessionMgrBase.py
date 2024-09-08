from typing import Union, Optional

import logging
import time
import json

import requests
from bs4 import BeautifulSoup


from .BotException import BotException
from .parser import Topic, Post



class SessionMgrBase():

    _logger = logging.getLogger(__qualname__)

    def __init__(self):
        self.__session = requests.Session()
        self.__last_status_code = None


    def login(self,
        id_username:  str,
        key_password: str,
        # These are for compatibility between SessionMgr v1 and v2
        token_directory:  str | type[None] = None,
        discord_bot_port: str | type[None] = None
    ):
        """
        Uses user credentials to log into osu!web just like a normal user would

        NOTE: This no longer works after captchas were added to the login page

        Parameters
        ----------
        id_username : str
            User's username or client id

        key_password : str
            User's password or client secret
        """
        raise NotImplementedError


    def edit_post(self, post_id: int | str, new_content: str, append: bool = False):
        raise NotImplementedError

    def get_post_bbcode(self, post_id: int | str):
        raise NotImplementedError


    def fetch_web_data(self, url: str) -> requests.Response:
        try:
            response = self.__session.get(url, timeout=10)
            self.__validate_response(response)
            return response
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            msg = f'Timed out while fetching url: {url}'
            self._logger.error(msg)
            raise BotException(self._logger, msg) from e
        #except requests.exceptions.ChunkedEncodingError as e:
        #    msg = 'Unable to fetch url: ' + str(url) + '\n' + str(e)
        #    raise BotException(self._logger, msg)
        except Exception as e:
            self._logger.exception(f'Unable to fetch url: {url}')
            raise


    def get_last_status_code(self) -> int:
        return self.__last_status_code


    def get_subforum(self, subforum_id: int | str, page: Optional[BeautifulSoup] = None) -> dict:
        subforum_url = f'https://osu.ppy.sh/community/forums/{subforum_id}'
        page = self.fetch_web_data(subforum_url)

        # Error checking
        if page.text.find("You shouldn&#039;t be here.") != -1:
            msg = f'Cannot access subforum with url {subforum_url}!'
            self._logger.error(msg)
            raise BotException(self._logger, msg)

        # \TODO: Maybe just create thread objects from thread enetries?
        root = BeautifulSoup(page.text, "lxml")
        try:
            # Get relevant sections of the HTML
            subforum_name   = None  # \TODO
            thread_entries  = root.find_all(class_='js-forum-topic-entry')
            thread_ids      = None  # \TODO
            thread_names    = [ entry.find_all(class_='forum-topic-entry__title')[0] for entry in thread_entries ]
            thread_authors  = [ entry.find_all(class_='user-name js-usercard')[0] for entry in thread_entries]
            thread_lastPost = [ [ child.find_all(class_='user-name js-usercard')[0] for child in entry.find_all(class_='u-ellipsis-overflow') ][0] for entry in thread_entries ]
            thread_lastTime = [ entry.find_all(class_='timeago')[0] for entry in thread_entries ]

            # Extract data
            thread_names    = [ name.text for name in thread_names ]
            thread_authors  = [ user.text for user in thread_authors ]
            thread_lastPost = [ user.text for user in thread_lastPost ]
            thread_lastTime = [ time.text for time in thread_lastTime ]

        except BotException as e:
            raise
        except Exception as e:
            self._logger.exception(f'{subforum_url} is no longer parsable :(')
            raise

        # Validate to make sure everything matches up as expected
        if not (len(thread_names) == len(thread_authors) == len(thread_lastPost) == len(thread_lastTime)):
            msg = f'Data mismatch; thread_names: {len(thread_names)}   thread_authors: {len(thread_authors)}    thread_lastPost: {len(thread_lastPost)}    thread_lastTime: {len(thread_lastTime)}'
            raise BotException(self._logger, msg)

        # Sanitize data
        thread_names    = [ name.replace('\n', '') for name in thread_names ]
        thread_lastPost = [ pstr.replace('\n', '') for pstr in thread_lastPost ]

        # Compile data
        data = {
            'subforum_id'     : subforum_id,
            'subforum_name'   : subforum_name,
            'thread_ids'      : thread_ids,
            'thread_names'    : thread_names,
            'thread_authors'  : thread_authors,
            'thread_lastpost' : thread_lastPost,
            'thread_lastTime' : thread_lastTime
        }

        return data


    def get_thread(self, thread_id: Union[int, str], page: Optional[requests.Response] = None, post_num: int = 0):
        thread_url = f'https://osu.ppy.sh/community/forums/topics/{thread_id}/?n={post_num}'
        if not page:
            page = self.fetch_web_data(thread_url)

        # Error checking
        msg = None
        if page.text.find("Page Missing") != -1:                msg = f'Topic with url {thread_url} does not exist!'
        if page.text.find("You shouldn&#039;t be here.") != -1: msg = f'Cannot access topic with url {thread_url}!'

        if msg:
            raise BotException(self._logger, msg)

        return Topic(BeautifulSoup(page.text, "lxml"))


    def get_post(self, post_id: Union[int, str], page: Optional[requests.Response] = None) -> Post:
        post_url = f'https://osu.ppy.sh/community/forums/posts/{post_id}'
        if not page:
            page = self.fetch_web_data(post_url)

        # Error checking
        msg = None
        if page.text.find("Page Missing") != -1:                msg = f'Post with url {post_url} does not exist!'
        if page.text.find("You shouldn&#039;t be here.") != -1: msg = f'Cannot access topic with url {post_url}!'
        if page.text.find("Account Verification") != -1:        msg = f'Cannot access topic with url {post_url} until logged in!'

        if msg:
            self._logger.error(msg)
            raise BotException(self._logger, msg)

        topic = Topic(BeautifulSoup(page.text, "lxml"))
        post  = None

        for topic_post in topic.posts:
            if topic_post.url != post_url:
                continue

            post = topic_post
            break

        if not post:
            msg = f'Unable to find post id {post_id} in thread id {topic.id}'
            self._logger.error(msg)
            raise BotException(self._logger, msg)

        return post


    def get_prev_post(self, ref_post: Post) -> Optional[Post]:
        posts = ref_post.topic.posts

        for i in range(len(posts)):
            if int(posts[len(posts) - i - 1].id) < int(ref_post.id):
                return posts[len(posts) - i - 1]  # Return the first post with a lesser post id than the given one

        # This is the first post
        return None


    def get_next_post(self, ref_post: Post) -> Optional[Post]:
        posts = ref_post.topic.posts

        for post in posts:
            if int(post.id) > int(ref_post.id):
                return post  # Return the first post with a greater post id than the given one

        # This is the last post
        return None


    def __validate_response(self, response: requests.Response):
        self.__last_status_code = response.status_code

        if response.status_code == 200: return 200  # Ok
        if response.status_code == 400: raise BotException('Error 400: Unable to process request')
        if response.status_code == 401: return 401  # Need to log in
        if response.status_code == 403: return 403  # Forbidden
        if response.status_code == 404: return 404  # Resource not found
        if response.status_code == 405: raise BotException('Error 405: Method not allowed')
        if response.status_code == 407: raise BotException('Error 407: Proxy authentication required')
        if response.status_code == 408: raise BotException('Error 408: Request timeout')
        if response.status_code == 429: return 429  # Too many requests
        if response.status_code == 500: return 500  # Internal server error
        if response.status_code == 502: raise BotException('Error 502: Bad Gateway')
        if response.status_code == 503: raise BotException('Error 503: Service unavailable')
        if response.status_code == 504: raise BotException('Error 504: Gateway timeout')


