from typing import Optional
from functools import cached_property

import logging
import datetime

from dateutil.parser import parse
from bs4 import BeautifulSoup

from .User import User
from .parser_error import ParserError

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .Topic import Topic



class Post():

    __logger = logging.getLogger(__qualname__)

    def __init__(self, topic: "Topic", root: BeautifulSoup):
        self.__topic  = topic
        self.__root   = root


    # Overload with the Topic object to ensure getTopic works for either objects
    @cached_property
    def topic(self) -> "Topic":
        return self.__topic


    @cached_property
    def creator(self) -> User:
        return User(self.__root)


    @cached_property
    def date(self) -> datetime.datetime:
        try:
            time = str(self.__root.find_all(class_='js-timeago')[0]['datetime']).strip()
            return parse(time)
        except Exception as e:
            raise ParserError(f'Unable to parse post date; {self.url}') from e


    @cached_property
    def post_num(self) -> str:
        try: return self.__root['data-post-position']
        except Exception as e:
            raise ParserError(f'Unable to parse post number; {self.url}') from e


    @cached_property
    def body_root(self) -> BeautifulSoup:
        try: return self.__root.find_all(class_='forum-post__body js-forum-post-edit--container')[0]
        except Exception as e:
            raise ParserError(f'Unable to parse post body; {self.url}') from e


    @cached_property
    def contents_root(self) -> BeautifulSoup:
        try: return self.__root.find_all(class_='forum-post-content')[0]
        except Exception as e:
            raise ParserError(f'Unable to parse post contents; {self.url}') from e


    @cached_property
    def contents_HTML(self) -> str:
        return str(self.contents_root).strip()


    @cached_property
    def contents_text(self) -> str:
        return str(self.contents_root.text).strip()


    @cached_property
    def content_markdown(self) -> str:
        html_str = str(self.contents_root).replace('\n', '')
        root = BeautifulSoup(html_str, 'lxml')

        for tag in root.find_all(True):
            if tag.name == 'iframe':
                tag.replace_with(f'{tag["src"]}')

            if tag.name == 'li':
                tag.insert_before('    • ')
                continue

            if tag.name == 'a':
                tag.replace_with(f'[{tag.text}]({tag["href"]})')
                continue

            if tag.name == 'img':
                try:
                    if 'smiley' in tag['class']:
                        tag.replace_with(':smile:')
                    else:
                        tag.replace_with(f'\n> [img]({tag["src"]})\n')
                        continue
                except:
                    continue

            if tag.name == 'br':
                tag.replace_with('\n')
                continue

            if tag.name == 'del':
                tag.insert_before('~~')
                tag.insert_after('~~')
                continue

            if tag.name == 'strong':
                tag.insert_before('**')
                tag.insert_after('**')
                continue

            if tag.name == 'em':
                tag.insert_before('*')
                tag.insert_after('*')
                continue

            if tag.name == 'h2':
                tag.insert_before('**')
                tag.insert_after('**\n')
                continue

            if tag.name == 'pre':
                tag.insert_before('```')
                tag.insert_after('```')
                continue

        # Keeps just the "<username> wrote:" part
        for tag in root.find_all(True):
            if tag.name == 'blockquote':
                try:
                    for tag_h4 in tag.find('h4'):
                        tag.replace_with(f'> **{tag_h4.string}** [...]\n\n')
                except TypeError:
                    tag.replace_with(f'> {tag.text}\n\n')

        return str(root.text).strip()


    @cached_property
    def url(self) -> str:
        try: return str(self.__root.find_all(class_='js-post-url')[0]['href']).strip()
        except Exception as e:
            raise ParserError('Unable to parse post url') from e


    @cached_property
    def prev_post(self) -> "Optional[Post]":
        post_roots = self.__topic.post_roots
        i = len(post_roots) - 1

        while True:
            post_id = Post(self.__topic, post_roots[i]).id
            if post_id == self.id: break
            if i <= 0: break
            i -= 1

        if i == 0:
            return None

        return Post(self.__topic, post_roots[i - 1])


    @cached_property
    def id(self) -> str:
        url = self.url
        return url[url.rfind('/') + 1:]
