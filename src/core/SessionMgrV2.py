import socket
import ossapi
import requests_oauthlib

from .BotConfig import BotConfig
from .SessionMgrBase import SessionMgrBase
from .DiscordClient import DiscordClient
from .BotException import BotException



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
        redirect_uri:       str | type[None]                = None,
        scopes:             list[str | ossapi.Scope]        = [ ossapi.Scope.PUBLIC ],
        domain:             str | ossapi.Domain             = ossapi.Domain.OSU,
        grant:              ossapi.Grant | str | type[None] = None,
        strict:             bool                            = False,

        token_directory:    str | type[None]                = None,
        token_key:          str | type[None]                = None,
        access_token:       str | type[None]                = None,
        refresh_token:      str | type[None]                = None,

        discord_bot_port:   str | type[None]                = None,
    ):
        self.__discord_bot_port = discord_bot_port
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


    def _new_authorization_grant(self, client_id: str, client_secret: str, redirect_uri: str, scopes: list[ossapi.Scope]):
        """
        Authenticates with the api from scratch on the authorization code grant.
        """
        self.log.info('Initializing authorization code')

        auto_refresh_kwargs = { 'client_id': client_id, 'client_secret': client_secret }
        session = requests_oauthlib.OAuth2Session(
            client_id,
            redirect_uri        = redirect_uri,
            auto_refresh_url    = self.token_url,
            auto_refresh_kwargs = auto_refresh_kwargs,
            token_updater       = self._save_token,
            scope               = [ scope.value for scope in scopes ],
        )

        self.log.debug('Sending url...')
        authorization_url, _state = session.authorization_url(self.auth_code_url)
        DiscordClient.request('/admin/post',{
            'contents' : f'Requesting authorization to the osu!api: {authorization_url}',
            'src'      : 'ForumBot'
        })

        # open up a temporary socket so we can receive the GET request to the callback url
        port = int(redirect_uri.rsplit(':', 1)[1].split('/')[0])
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.bind(('localhost', port))
        serversocket.listen(1)
        serversocket.settimeout(60)
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

    __instance = None

    def __new__(cls):
        """
        Singleton
        """
        if not cls.__instance:
            cls.__instance = super().__new__(cls)
            cls.__osu_apiv2 = None

        return cls.__instance


    def __init__(self):
        SessionMgrBase.__init__(self)


    def login(self):
        if isinstance(self.__osu_apiv2, OssapiCustom):
            return

        self._logger.info('Authorizing osu!api v2...')

        self.__osu_apiv2 = OssapiCustom(
            BotConfig['Core']['osuapiv2_client_id'],
            BotConfig['Core']['osuapiv2_client_secret'],
            redirect_uri       = 'http://localhost:8000',
            scopes             = [ ossapi.Scope.FORUM_WRITE ],
            grant              = 'authorization',

            token_directory  = BotConfig['Core']['osuapiv2_token_dir'],
            discord_bot_port = BotConfig['Core']['discord_bot_port'],
        )


    def get_post_bbcode(self, post_id: int | str):
        # Requires `GET /forums/posts/{post}` endpoint to be implemented
        # See: https://github.com/ppy/osu-web/issues/7486
        raise NotImplementedError


    def edit_post(self, post_id: int | str, new_content: str, append: bool = False):
        post_id = int(post_id)
        self.login()

        if append:
            bbcode = self.get_post_bbcode(post_id)
            bbcode += new_content

        # [2024.09.15] TODO: If client grant expires, this will throw an error
        #   this should be handled via a login and a retry
        try: self.__osu_apiv2.forum_edit_post(post_id, new_content)
        except Exception as e:
            msg = f'Unable to edit post id: {post_id}; {e}'
            raise BotException(msg) from e


SessionMgrV2 = SessionMgrV2()
