import time
import json

import requests
from bs4 import BeautifulSoup

from .SessionMgrBase import SessionMgrBase
from core.BotException import BotException



class SessionMgrV1(SessionMgrBase):
    """
    Legacy session manager that scrapes HTML data.

    NOTE: login no longer works since captchas were added on the login page
        This means web info can be read, but the posts/forums can't be edited
    """

    def __init__(self):
        SessionMgrBase.__init__(self)
        self.__logged_in = False


    def __del__(self):
        self.__logged_in = False


    def login(self,
        username: str,
        password: str,
        # These are for compatibility between SessionMgr v1 and v2
        mailtrap_api_token: str = None,
        mailtrap_addr_src:  str = None,
        email_addr_dst:     str = None
    ):
        """
        Uses user credentials to log into osu!web just like a normal user would

        NOTE: This no longer works after captchas were added to the login page

        Parameters
        ----------
        username : str
            User's username

        password : str
            User's password
        """
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
                'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Referer'    : 'https://osu.ppy.sh/home',
            }

            try: response = self.__session.post('https://osu.ppy.sh/session', data=login_data, headers=headers)
            except Exception:
                raise BotException(self._logger, 'Unable to log in')

            self.__validate_response(response)

            if response.status_code != 200:
                if response.status_code == 429:
                    self._logger.warning('Too many login requests; Taking a 5 min nap . . . ')
                    time.sleep(5*60)  # Too many requests; Take 5 min nap
                    continue
                if response.status_code == 403:
                    raise BotException(self._logger, 'Invalid login. Cannot continue!')
                if response.status_code == 422:
                    raise BotException(self._logger, 'Invalid login. Fill in `web_username` and `web_password` in config.yaml')
                else:
                    raise BotException(self._logger, f'Unable to log in; Status code: {response.status_code}')

            break

        # Validate log in
        response = self.fetch_web_data('https://osu.ppy.sh')
        if not 'XSRF-TOKEN' in response.cookies:
            raise BotException(self._logger, f'Unable to log in; Cookies indicate login failed!')

        self.__check_account_verification(response)
        self.__logged_in = True

        return


    def __check_account_verification(self, response: requests.Response):
        """
        The login process requires the user to acknowledge login via email.
        This checks if the user has acknowledged the email login notification.
        """
        check = False
        while True:
            if response.text.find('Account Verification') == -1:
                break

            if not check:
                self._logger.warning('Need response to verification email before continuing')
                check = True

            response = self.fetch_web_data('https://osu.ppy.sh')
            time.sleep(5)  # Check every minute until responded to email


    def get_post_bbcode(self, post_id: int | str):
        if not self.__logged_in:
            raise BotException(self._logger, 'Must be logged in first')

        response = self.fetch_web_data(f'https://osu.ppy.sh/community/forums/posts/{post_id}/edit')
        if response.status_code == 403:
            msg = f'Unable to retrieve bbcode for posts that are not yours; post_id: {post_id}'
            raise BotException(self._logger, msg)

        root = BeautifulSoup(response.text, "lxml")

        try: bbcode = root.find('textarea').renderContents().decode('utf-8')
        except Exception as e:
            msg = f'Unable to parse bbcode for post id: {post_id}; {e}\nRoot: {root}'
            raise BotException(self._logger, msg) from e

        return bbcode


    def edit_post(self, post_id: int | str, new_content: str, append: bool = False):
        if not self.__logged_in:
            raise BotException(self._logger, 'Must be logged in first')

        try:
            response = self.fetch_web_data('https://osu.ppy.sh')
            data = {
                'body'    : new_content if not append else (self.get_post_bbcode(post_id) + new_content),
                '_method' : 'PATCH',
                #'_token'  : response.cookies['XSRF-TOKEN']
            }

            response = self.__session.post(f'https://osu.ppy.sh/community/forums/posts/{post_id}', data=data)
            self.__validate_response(response)  # TODO: Log in if not logged in?

            try:
                response = json.loads(response.text)
                if 'error' in response:
                    msg = f'Unable to edit post id: {response["error"]}'
                    raise BotException(self._logger, msg)
            except:
                pass  # Then it went through ok

        except Exception as e:
            msg = f'Unable to edit post id: {post_id}; {e}'
            raise BotException(self._logger, msg) from e
