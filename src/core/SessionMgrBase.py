from typing import Optional

import logging
import requests

from bs4 import BeautifulSoup

from .BotException import BotException
from .parser import Topic, Post



class SessionMgrBase():

    _logger = logging.getLogger(__qualname__)

    def __init__(self):
        self.__session = requests.Session()
        self.__last_status_code = None


    def login(self):
        """
        Authenticates with the osu! forums via credentials stored in BotConfig. Meant to be overridden
        """
        raise NotImplementedError


    def edit_post(self, post_id: int | str, new_content: str, append: bool = False) -> None:
        """
        Edits a post on the osu! forums. Meant to be overridden

        Parameters
        ----------
        post_id : int | str
            The id of the post to edit.
        new_content : str
            The new bbcode content to replace the old one with.
        append : bool, optional
            Whether to append the new content to the old one, by default False.
        """
        raise NotImplementedError


    def get_post_bbcode(self, post_id: int | str) -> str:
        """
        Retrieves the bbcode of a post on the osu! forums. Meant to be overridden

        Parameters
        ----------
        post_id : int | str
            The id of the post to retrieve the bbcode from.

        Returns
        -------
        str
            The bbcode content of the post.
        """
        raise NotImplementedError


    def fetch_web_data(self, url: str) -> requests.Response:
        """
        Fetches web data from the given url

        Parameters
        ----------
        url : str
            The url to fetch

        Raises
        ------
        BotException
            If the request times out or if there is a connection error

        Returns
        -------
        requests.Response
            The response containing the fetched web data
        """
        try: response = self.__session.get(url, timeout=10)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise BotException(f'Timed out while fetching url: {url}', False)

        self.__validate_response(response)
        return response


    def get_last_status_code(self) -> int:
        """
        Returns the status code of the last request made.

        Returns
        -------
        int
            The status code of the last request made.
        """
        return self.__last_status_code



    def get_subforum(self, subforum_id: int | str, page: Optional[BeautifulSoup] = None) -> dict:
        """
        Retrieves a subforum with the given id.

        Parameters
        ----------
        subforum_id : int | str
            The id of the subforum to retrieve.
        page : BeautifulSoup | type[None]
            The contents of the subforum page to parse. If not provided, it will be fetched.

        Raises
        ------
        BotException
            - If the request times out or if there is a connection error
            - If html produces different number of thread names, authors, ids, or timestamps
        Exception
            - If the html cannot be parsed

        Returns
        -------
        dict
            A dictionary containing the subforum's details
        """
        subforum_url = f'https://osu.ppy.sh/community/forums/{subforum_id}'
        if not page:
            page = self.fetch_web_data(subforum_url)

        # Error checking
        if page.text.find('You shouldn&#039;t be here.') != -1:
            raise BotException(f'Cannot access subforum with url {subforum_url}!')

        # \TODO: Maybe just create thread objects from thread entries?
        root = BeautifulSoup(page.text, 'lxml')
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
        except Exception as e:
            raise Exception(f'{subforum_url} is no longer parsable :(') from e

        # Validate to make sure everything matches up as expected
        if not (len(thread_names) == len(thread_authors) == len(thread_lastPost) == len(thread_lastTime)):
            raise BotException(
                f'Data mismatch\n'
                f'    thread_names:    {len(thread_names)}\n'
                f'    thread_authors:  {len(thread_authors)}\n'
                f'    thread_lastPost: {len(thread_lastPost)}\n'
                f'    thread_lastTime: {len(thread_lastTime)}'
            )

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


    def get_thread(self, thread_id: int | str, page: Optional[requests.Response] = None, post_num: int = 0) -> Topic:
        """
        Retrieves a thread with the given thread id.

        Parameters
        ----------
        thread_id : int | str
            The id of the thread to retrieve.
        page : Optional[requests.Response]
            A pre-fetched page of the thread. If None, then the page will be fetched from the web.
        post_num : int
            The page number of the thread to fetch. Defaults to 0 (the first page).

        Raises
        ------
        BotException
            If the thread does not exist or if the page is not accessible.

        Returns
        -------
        Topic
            The retrieved thread.
        """
        thread_url = f'https://osu.ppy.sh/community/forums/topics/{thread_id}/?n={post_num}'
        if not page:
            page = self.fetch_web_data(thread_url)

        # Error checking
        if page.text.find('Page Missing') != -1:
            raise BotException(f'Topic with url {thread_url} does not exist!')
        if page.text.find('You shouldn&#039;t be here.') != -1:
            raise BotException(f'Cannot access topic with url {thread_url}!')

        return Topic(BeautifulSoup(page.text, 'lxml'))


    def get_post(self, post_id: int | str, page: Optional[requests.Response] = None) -> Post:
        """
        Retrieves a post with the given post id.

        Parameters
        ----------
        post_id : int | str
            The id of the post to retrieve.

        page : requests.Response | type[None]
            The web data of the post to retrieve from. If not given, the web data will be retrieved from the internet.

        Raises
        ------
        BotException
            If post is missing or cannot be accessed.

        Returns
        -------
        Post
            The retrieved post.
        """
        post_url = f'https://osu.ppy.sh/community/forums/posts/{post_id}'
        if not page:
            page = self.fetch_web_data(post_url)

        # Error checking
        if page.text.find('Page Missing') != -1:
            raise BotException(f'Post with url {post_url} does not exist!')
        if page.text.find('You shouldn&#039;t be here.') != -1:
            raise BotException(f'Cannot access topic with url {post_url}!')
        if page.text.find('Account Verification') != -1:
            raise BotException(f'Cannot access topic with url {post_url} until logged in!')

        topic = Topic(BeautifulSoup(page.text, 'lxml'))
        for topic_post in topic.posts:
            if topic_post.url == post_url:
                return topic_post

        raise BotException(f'Unable to find post id {post_id} in thread id {topic.id}')


    def get_prev_post(self, ref_post: Post) -> Optional[Post]:
        """
        Returns the post before the given reference post in the topic.

        Parameters
        ----------
        ref_post: Post
            The reference post to find the previous post of.

        Returns
        -------
        Post | None
            The post before the reference post, or None if it is the first post in the topic.
        """
        posts = ref_post.topic.posts

        for post in reversed(posts):
            if int(post.id) < int(ref_post.id):
                # Return the first post with a lesser post id than the given one
                return post

        return ref_post.prev_post


    def get_next_post(self, ref_post: Post) -> Optional[Post]:
        """
        Returns the post after the given reference post in the topic.

        Parameters
        ----------
        ref_post: Post
            The reference post to find the next post of.

        Returns
        -------
        Post | None
            The post that comes after the given post, or None if there is no next post.
        """
        posts = ref_post.topic.posts

        for post in posts:
            if int(post.id) > int(ref_post.id):
                return post

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


