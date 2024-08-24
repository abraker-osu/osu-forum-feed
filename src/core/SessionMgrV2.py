from typing import Optional

import logging
import socket

import requests
import webbrowser
import mailtrap
import ossapi
import requests_oauthlib

from .SessionMgrBase import SessionMgrBase
from core.BotException import BotException




class OssapiCustom(ossapi.Ossapi):
    """
    A wrapper around osu! api v2. The main entry point for ossapi.

    Overrides the opening of browser for oath grant. Instead it sends the
    authorization page link to the supplied email address where the user
    can then accept access there. Mimics old authorization behavior with
    user password login in SessionMgrV1.

    Also sets a 10 second timeout for authorization callback so that this does
    not hang indefinitely.

    Parameters
    ----------
    client_id: int
        The id of the client to authenticate with.

    client_secret: str
        The secret of the client to authenticate with.

    redirect_uri: str
        The redirect uri for the client. Must be passed if using the
        authorization code grant. This must exactly match the redirect uri on
        the client's settings page. Additionally, in order for ossapi to receive
        authentication from this redirect uri, it must be a port on localhost,
        e.g. "http://localhost:3914/". You can change your client's redirect uri
        from its settings page.

    scopes: List[str]
        What scopes to request when authenticating.

    grant: Grant or str
        Which oauth grant (aka flow) to use when authenticating with the api.
        The osu api offers the client credentials (pass "client" for this
        parameter) and authorization code (pass "authorization" for this
        parameter) grants.
        |br|
        The authorization code grant requires user interaction to authenticate
        the first time, but grants full access to the api. In contrast, the
        client credentials grant does not require user interaction to
        authenticate, but only grants guest user access to the api. This means
        you will not be able to do things like download replays on the client
        credentials grant.
        |br|
        If not passed, the grant will be automatically inferred as follows: if
        ``redirect_uri`` is passed, use the authorization code grant. If
        ``redirect_uri`` is not passed, use the client credentials grant.

    strict: bool
        Whether to run in "strict" mode. In strict mode, ossapi will raise an
        exception if the api returns an attribute in a response which we didn't
        expect to be there. This is useful for developers which want to catch
        new attributes as they get added. More checks may be added in the future
        for things which developers may want to be aware of, but normal users do
        not want to have an exception raised for.
        |br|
        If you are not a developer, you are very unlikely to want to use this
        parameter.

    token_directory: str
        If passed, the given directory will be used to store and retrieve token
        files instead of locally wherever ossapi is installed. Useful if you
        want more control over token files.

    token_key: str
        If passed, the given key will be used to name the token file instead of
        an automatically generated one. Note that if you pass this, you are
        taking responsibility for making sure it is unique / unused, and also
        for remembering the key you passed if you wish to eg remove the token in
        the future, which requires the key.

    access_token: str
        Access token from the osu! api. Allows instantiating
        :class:`~ossapi.ossapiv2.Ossapi` after manually authenticating with the
        osu! api.

    refresh_token: str
        Refresh token from the osu! api. Allows instantiating
        :class:`~ossapi.ossapiv2.Ossapi` after manually authenticating with the
        osu! api. Optional if using :data:`Grant.CLIENT_CREDENTIALS
        <ossapi.ossapiv2.Grant.CLIENT_CREDENTIALS>`.

    domain: Domain or str
        The domain to retrieve information from. This defaults to
        :data:`Domain.OSU <ossapi.ossapiv2.Domain.OSU>`, which corresponds to
        osu.ppy.sh, the main website.
        |br|
        To retrieve information from dev.ppy.sh, specify
        :data:`Domain.DEV <ossapi.ossapiv2.Domain.DEV>`.
        |br|
        See :doc:`Domains <domains>` for more about domains.
    """
    def __init__(self, client_id: int, client_secret: str,
        redirect_uri:       Optional[str]                   = None,
        scopes:             list[str | ossapi.Scope]        = [ ossapi.Scope.PUBLIC ],
        domain:             str | ossapi.Domain             = ossapi.Domain.OSU,
        grant:              Optional[ossapi.Grant | str]    = None,
        strict:             bool                            = False,

        token_directory:    Optional[str]                   = None,
        token_key:          Optional[str]                   = None,
        access_token:       Optional[str]                   = None,
        refresh_token:      Optional[str]                   = None,

        mailtrap_api_token: Optional[str]                   = None,
        mailtrap_addr_src:  Optional[str]                   = None,
        email_addr_dst:     Optional[str]                   = None,
    ):
        self.__mailtrap_api_token = mailtrap_api_token
        self.__mailtrap_addr_src  = mailtrap_addr_src
        self.__email_addr_dst     = email_addr_dst

        ossapi.Ossapi.__init__(self,
            client_id, client_secret,
            domain          = domain,
            redirect_uri    = redirect_uri,
            scopes          = scopes,
            grant           = grant,
            strict          = strict,
            token_directory = token_directory,
            token_key       = token_key,
            access_token    = access_token,
            refresh_token   = refresh_token
        )

        self.log.debug('Ossapi init done')


    def _send_email(self, authorization_url: str):
        self.log.info(f'Sending authorization email to {self.__email_addr_dst}...')

        mailtrap_client = mailtrap.MailtrapClient(token=self.__mailtrap_api_token)
        mail = mailtrap.Mail(
            sender = mailtrap.Address(email=self.__mailtrap_addr_src, name='osu forumbot'),
            to = [
                mailtrap.Address(email=self.__email_addr_dst)
            ],
            subject = 'osu!api v2 authorization',
            text    = f'The forumbot is requesting authorization to the osu!api: {authorization_url}',
        )

        try: mailtrap_client.send(mail)
        except mailtrap.APIError as e:
            self.log.warning(e)
            raise


    def _new_authorization_grant(self, client_id: str, client_secret: str, redirect_uri: str, scopes: list[ossapi.Scope]):
        """
        Authenticates with the api from scratch on the authorization code grant.
        """
        self.log.info('initializing authorization code')

        auto_refresh_kwargs = { 'client_id': client_id, 'client_secret': client_secret }
        session = requests_oauthlib.OAuth2Session(
            client_id,
            redirect_uri        = redirect_uri,
            auto_refresh_url    = self.token_url,
            auto_refresh_kwargs = auto_refresh_kwargs,
            token_updater       = self._save_token,
            scope               = [ scope.value for scope in scopes ],
        )

        authorization_url, _state = session.authorization_url(self.auth_code_url)
        try: self._send_email(authorization_url)
        except:
            self.log.warning('Failed to send email. Trying to open authorization url in browser instead...')
            webbrowser.open(authorization_url)

        # open up a temporary socket so we can receive the GET request to the callback url
        port = int(redirect_uri.rsplit(':', 1)[1].split('/')[0])
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.bind(('localhost', port))
        serversocket.listen(1)
        serversocket.settimeout(10)
        connection, _ = serversocket.accept()

        # arbitrary "large enough" byte receive size
        self.log.info('Awaiting notification from callback...')
        data = str(connection.recv(8192))
        connection.send(b'HTTP/1.0 200 OK\n')
        connection.send(b'Content-Type: text/html\n')
        connection.send(b'\n')
        connection.send(
            b"""<html><body>
            <h2>Ossapi has received your authentication.</h2> You
            may now close this tab safely.
            </body></html>
            """
        )

        connection.close()
        serversocket.close()

        code  = data.split('code=')[1].split('&state=')[0]
        token = session.fetch_token(
            self.token_url, client_id=client_id, client_secret=client_secret, code=code
        )
        self._save_token(token)

        return session



class SessionMgrV2(SessionMgrBase):

    def __init__(self):
        SessionMgrBase.__init__(self)
        self.__osu_apiv2 = None


    def login(self,
        client_id:          int,
        client_secret:      str,
        mailtrap_api_token: str = None,
        mailtrap_addr_src:  str = None,
        email_addr_dst:     str = None
    ):
        if not isinstance(self.__osu_apiv2, type(None)):
            return

        self._logger.info('Authorizing osu!api v2...')

        self.__osu_apiv2 = OssapiCustom(
            client_id, client_secret,
            redirect_uri       = 'http://localhost:8000',
            scopes             = [ ossapi.Scope.FORUM_WRITE ],
            grant              = 'authorization',

            mailtrap_api_token = mailtrap_api_token,
            mailtrap_addr_src  = mailtrap_addr_src,
            email_addr_dst     = email_addr_dst
        )


    def get_post_bbcode(self, post_id: int | str):
        # Requires `GET /forums/posts/{post}` endpoint to be implemented
        # See: https://github.com/ppy/osu-web/issues/7486
        raise NotImplementedError


    def edit_post(self, post_id: int | str, new_content: str, append: bool = False):
        post_id = int(post_id)

        if isinstance(self.__osu_apiv2, type(None)):
            raise BotException(self._logger, 'Must be logged in first')

        if append:
            bbcode = self.get_post_bbcode(post_id)
            bbcode += new_content

        try: self.__osu_apiv2.forum_edit_post(post_id, new_content)
        except Exception as e:
            msg = f'Unable to edit post id: {post_id}; {e}'
            raise BotException(self._logger, msg) from e
