from typing import Union, Optional

import logging
import requests
import time
import json

from bs4 import BeautifulSoup

from core.BotException import BotException
from .parser import Topic, Post



class SessionMgr():

    def __init__(self):
        self.__logger  = logging.getLogger(__class__.__name__)
        self.__session = requests.session()

        self.__logged_in = False
        self.__last_status_code = None


    def __del__(self):
        self.__session = None
        self.__logged_in = False


    def login(self, username: str, password: str):
        if self.__logged_in:
            return

        # While being told there are too many login requests, attempt to log in
        while True:
            # For some reason web now needs a token for login
            response = self.fetch_web_data('https://osu.ppy.sh')
            self.__validate_response(response)

            root = BeautifulSoup(response.text, 'lxml')
            token = root.find('input', {'name' : '_token'})['value']

            login_data = { '_token' : token, 'username': username, 'password' : password }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0',
                'Referer' : 'https://osu.ppy.sh/home'
            }

            try: response = self.__session.post('https://osu.ppy.sh/session', data=login_data, headers=headers)
            except Exception:
                raise BotException(self.__logger, 'Unable to log in')

            self.__validate_response(response)

            if response.status_code != 200:
                if response.status_code == 429:
                    self.__logger.warning('Too many login requests; Taking a 5 min nap . . . ')
                    time.sleep(5*60)  # Too many requests; Take 5 min nap
                    continue
                if response.status_code == 403:
                    raise BotException(self.__logger, 'Invalid login. Cannot continue!')
                if response.status_code == 422:
                    raise BotException(self.__logger, 'Invalid login. Fill in `web_username` and `web_password` in config.py')
                else:
                    raise BotException(self.__logger, f'Unable to log in; Status code: {response.status_code}')

            break

        # Validate log in
        response = self.fetch_web_data('https://osu.ppy.sh')
        if not 'XSRF-TOKEN' in response.cookies:
            raise BotException(self.__logger, 'Unable to log in; Cookies indicate login failed!')

        self.__check_account_verification(response)
        self.__logged_in = True

        return


    def __check_account_verification(self, response: requests.Response):
        check = False
        while True:
            if response.text.find('Account Verification') == -1: break
            if not check:
                self.__logger.warn('Need response to verification email before continuing')
                check = True

            response = self.fetch_web_data('https://osu.ppy.sh')
            time.sleep(5)  # Check every minute until responded to email


    def fetch_web_data(self, url: str) -> requests.Response:
        try:
            response = self.__session.get(url, timeout=10)
            self.__validate_response(response)
            return response
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            msg = f'Timed out while fetching url: {url}'
            self.__logger.error(msg)
            raise BotException(self.__logger, msg) from e
        #except requests.exceptions.ChunkedEncodingError as e:
        #    msg = 'Unable to fetch url: ' + str(url) + '\n' + str(e)
        #    raise BotException(self.__logger, msg)
        except Exception as e:
            self.__logger.exception(f'Unable to fetch url: {url}')
            raise


    def get_last_status_code(self) -> int:
        return self.__last_status_code


    def get_post_bbcode(self, post_id: Union[int, str]):
        if not self.__logged_in:
            self.login()

        # TODO: Log in if not logged in?
        response = self.fetch_web_data(f'https://osu.ppy.sh/community/forums/posts/{post_id}/edit')

        if response.status_code == 403:
            msg = f'Unable to retrieve bbcode for posts that are not yours; post_id: {post_id}'
            raise BotException(self.__logger, msg)

        root = BeautifulSoup(response.text, "lxml")

        try: bbcode = root.find('textarea').renderContents().decode('utf-8')
        except Exception as e:
            msg = f'Unable to parse bbcode for post id: {post_id}; {e}'
            raise BotException(self.__logger, msg) from e

        return bbcode


    def edit_post(self, post_id: Union[int, str], new_content: str, append: bool = False):
        if not self.__logged_in:
            self.login()

        try:
            response = self.fetch_web_data('https://osu.ppy.sh')
            data = {
                'body'    : new_content if not append else (self.get_post_bbcode(post_id) + new_content),
                '_method' : 'PATCH',
                '_token'  : response.cookies['XSRF-TOKEN']
            }

            response = self.__session.post(f'https://osu.ppy.sh/community/forums/posts/{post_id}', data=data)
            self.__validate_response(response)  # TODO: Log in if not logged in?

            try:
                response = json.loads(response.text)
                if 'error' in response:
                    msg = f'Unable to edit post id: {response["error"]}'
                    raise BotException(self.__logger, msg)
            except:
                pass  # Then it went through ok

        except Exception as e:
            msg = f'Unable to edit post id: {post_id}; {e}'
            raise BotException(self.__logger, msg) from e


    def get_subforum(self, subforum_id: Union[int, str], page: BeautifulSoup = None) -> dict:
        subforum_url = f'https://osu.ppy.sh/community/forums/{subforum_id}'
        page = self.fetch_web_data(subforum_url)

        # Error checking
        if page.text.find("You shouldn&#039;t be here.") != -1:
            msg = f'Cannot access subforum with url {subforum_url}!'
            self.__logger.error(msg)
            raise BotException(self.__logger, msg)

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
            self.__logger.exception(f'{subforum_url} is no longer parsable :(')
            raise

        # Validate to make sure everything matches up as expected
        if not (len(thread_names) == len(thread_authors) == len(thread_lastPost) == len(thread_lastTime)):
            msg = f'Data mismatch; thread_names: {len(thread_names)}   thread_authors: {len(thread_authors)}    thread_lastPost: {len(thread_lastPost)}    thread_lastTime: {len(thread_lastTime)}'
            raise BotException(self.__logger, msg)

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
            self.__logger.error(msg)
            raise BotException(self.__logger, msg)

        topic = Topic(BeautifulSoup(page.text, "lxml"), self.__logger)
        post  = None

        for topic_post in topic.posts:
            if topic_post.url != post_url:
                continue

            post = topic_post
            break

        if not post:
            msg = f'Unable to find post id {post_id} in thread id {topic.id}'
            self.__logger.error(msg)
            raise BotException(self.__logger, msg)

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


