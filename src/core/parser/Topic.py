from typing import Optional
from functools import cached_property

import datetime
import logging
from bs4 import BeautifulSoup

from .Post import Post
from .parser_error import ParserError


class Topic():

    __logger = logging.getLogger(__qualname__)

    def __init__(self, root: BeautifulSoup):
        self.__root = root


    # Overload with the Post object to ensure getTopic works for either objects
    @cached_property
    def topic(self):
        return self


    @cached_property
    def subforum_id(self) -> int:
        try:
            subforum_path_root = self.__root.find_all(class_='header-v4__row header-v4__row--bar')[0]
            subforum_url = subforum_path_root.find_all(class_='header-nav-v4__link')[-1].get('href')
            return int(subforum_url[subforum_url.rfind('/') + 1:])
        except Exception as e:
            raise ParserError(f'Unable to parse topic subforum id; {self.url}: {e}') from e


    @cached_property
    def subforum_name(self) -> str:
        try:
            subforum_path_root = self.__root.find_all(class_='header-v4__row header-v4__row--bar')[0]
            return subforum_path_root.find_all(class_='header-nav-v4__item')[-1].text.strip()
        except Exception as e:
            raise ParserError(f'Unable to parse topic subforum name; {self.url}: {e}') from e


    @cached_property
    def date(self) -> datetime.datetime:
        try: return self.first_post.date
        except Exception as e:
            raise ParserError(f'Unable to parse topic date; {self.url}: {e}') from e


    @cached_property
    def creator(self) -> str:
        try: return self.first_post.creator
        except Exception as e:
            raise ParserError(f'Unable to parse topic creator; {self.url}: {e}') from e


    # \FIXME: Apperently some threads can have no title like this one: https://osu.ppy.sh/forum/t/751805
    @cached_property
    def name(self) -> str:
        try: return self.__root.find_all(class_='forum-topic-title__title forum-topic-title__title--display')[0].text.strip()
        except Exception as e:
            raise ParserError(f'Unable to parse topic name; {self.url}: {e}') from e


    @cached_property
    def url(self) -> str:
        try: return self.__root.find_all(class_='forum-topic-floating-header__title-link')[0]['href'].strip()
        except Exception as e:
            raise ParserError(f'Unable to parse topic url; {self.url}: {e}') from e


    @cached_property
    def id(self) -> int:
        url = self.url
        return int(url[url.rfind('/') + 1:])


    # \TODO: Finish implementation
    @cached_property
    def status(self):
        # \TODO
        '''
        status = root.find_all(class_='js-forum-topic-reply--container')[0].text.strip()
        if status == 'Can not reply to a locked thread.':
            self.status = 'locked'
        else:
            self.status = 'open'
        '''

        raise NotImplementedError


    @cached_property
    def post_count(self) -> int:
        try: return int(self.__root.find_all(class_='js-forum__total-count')[0].text.strip().replace(',', ''))
        except Exception as e:
            raise ParserError(f'Unable to parse post count; {self.url}') from e


    def findPost(self, root: BeautifulSoup, post_url: str) -> Optional[Post]:
        for post in self.posts:
            if Post(None).url == post_url:
                return Post(post)

        return None


    @cached_property
    def post_roots(self) -> BeautifulSoup:
        try: return self.__root.find_all(class_='js-forum-post')
        except Exception as e:
            raise ParserError(f'Unable to parse topic posts; {self.url}: {e}') from e


    @cached_property
    def first_post(self) -> Post:
        if len(self.post_roots) == 0:
            raise ParserError(f'No posts found in thread; {self.url}')

        return Post(self, self.post_roots[0])


    # \TODO: Maybe this needs to be more efficient; Do only the ones that are needed to be done
    #        and keep track of which posts were not parsed
    # Only gets visible posts (max 20)
    @cached_property
    def posts(self) -> "list[Post]":
        posts = [ self.first_post ]
        if len(posts) < min(int(self.post_count), 20):
            for post in self.post_roots[1:]:
                posts.append(Post(self, post))

        return posts
