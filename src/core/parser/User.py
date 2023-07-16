from functools import cached_property

import re
from bs4 import BeautifulSoup


class User():

    def __init__(self, root: BeautifulSoup):
        self.__root = root


    @cached_property
    def id(self) -> str:
        url = self.url
        return url[url.rfind('/') + 1:]


    @cached_property
    def name(self) -> str:
        try: return self.__root.find_all(class_='forum-post-info__row forum-post-info__row--username js-usercard')[0].text.strip()
        except:
            return ''


    @cached_property
    def avatar(self) -> str:
        try:
            post_user_avatar = self.__root.find_all(class_='avatar avatar--forum')[0].get('style')
            if not post_user_avatar:
                post_user_avatar = "background-image: url('');"
        except:
            post_user_avatar = "background-image: url('');"

        avatar = re.findall('background-image: url\(\'(.*?)\'\);', post_user_avatar)[0]
        if avatar == '/images/layout/avatar-guest.png':
            return 'https://osu.ppy.sh/images/layout/avatar-guest.png'
        else:
            return avatar


    @cached_property
    def url(self) -> str:
        try:
            url = self.__root.find_all(class_='avatar avatar--forum')[0].get('href')
            if not url:
                return "https://osu.ppy.sh/users/-1"
        except:
            return "https://osu.ppy.sh/users/-1"

        return url



