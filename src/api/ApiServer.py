import os
import platform
import asyncio
import socket
import warnings

from typing import Optional, Sequence

import logging
import threading

import asyncio
import uvicorn
import fastapi

from core.BotConfig import BotConfig

from .Cmd import Cmd
from .CommandProcessor import CommandProcessor

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.BotBase import BotBase


class UvicornServerPatch(uvicorn.Server):
    """
    Patches the original `startup` behavior as of uvicorn 0.21.1
    Fixes case(s):
        - When port is already taken the server would fail to bind to the port. This would
          proceed to call `sys.exit(1)` after shutting down, effectively terminating the
          entire python app. This is undesired since the this server is a service that resides
          in a larger overall app. ctrl+f "PATCH" for code commentating fix.
    """

    __logger = logging.getLogger('UvicornServerPatch')

    async def startup(self: uvicorn.Server, sockets: Optional[list[socket.socket]] = None) -> None:
        await self.lifespan.startup()
        if self.lifespan.should_exit:
            self.should_exit = True
            return

        config = self.config

        def create_protocol(_loop: Optional[asyncio.AbstractEventLoop] = None,) -> asyncio.Protocol:
            return config.http_protocol_class(  # type: ignore[call-arg]
                config=config,
                server_state=self.server_state,
                app_state=self.lifespan.state,
                _loop=_loop,
            )

        loop = asyncio.get_running_loop()

        listeners: Sequence[socket.SocketType]
        if sockets is not None:
            # Explicitly passed a list of open sockets.
            # We use this when the server is run from a Gunicorn worker.

            def _share_socket(sock: socket.SocketType,) -> socket.SocketType:
                # Windows requires the socket be explicitly shared across
                # multiple workers (processes).
                from socket import fromshare

                sock_data = sock.share(os.getpid())
                return fromshare(sock_data)

            self.servers = []
            for sock in sockets:
                if config.workers > 1 and platform.system() == 'Windows':
                    sock = _share_socket(sock)

                server = await loop.create_server(
                    create_protocol,
                    sock    = sock,
                    ssl     = config.ssl,
                    backlog = config.backlog
                )
                self.servers.append(server)

            listeners = sockets

        elif config.fd is not None:  # pragma: py-win32
            # Use an existing socket, from a file descriptor.
            sock = socket.fromfd(config.fd, socket.AF_UNIX, socket.SOCK_STREAM)
            server = await loop.create_server(
                create_protocol,
                sock    = sock,
                ssl     = config.ssl,
                backlog = config.backlog
            )
            assert server.sockets is not None  # mypy
            listeners = server.sockets
            self.servers = [server]

        elif config.uds is not None:  # pragma: py-win32
            # Create a socket using UNIX domain socket.
            uds_perms = 0o666
            if os.path.exists(config.uds):
                uds_perms = os.stat(config.uds).st_mode

            server = await loop.create_unix_server(
                create_protocol,
                path    = config.uds,
                ssl     = config.ssl,
                backlog = config.backlog
            )

            os.chmod(config.uds, uds_perms)

            assert server.sockets is not None  # mypy
            listeners = server.sockets
            self.servers = [server]

        else:
            # Standard case. Create a socket from a host/port pair.
            try:
                server = await loop.create_server(
                    create_protocol,
                    host    = config.host,
                    port    = config.port,
                    ssl     = config.ssl,
                    backlog = config.backlog,
                )
            except OSError as exc:
                UvicornServerPatch.__logger.error(exc)
                await self.lifespan.shutdown()
                return  # PATCH: Replaces the `sys.exit(1)` of original implementation

            assert server.sockets is not None
            listeners = server.sockets
            self.servers = [server]

        if sockets is None:
            self._log_started_message(listeners)
        else:
            # We're most likely running multiple workers, so a message has already been
            # logged by `config.bind_socket()`.
            pass

        self.started = True


class ApiServer():

    __app     = fastapi.FastAPI()
    __cmd     = None
    __logger  = logging.getLogger(__qualname__)

    __init    = False
    __server  = None

    __loop    = None
    __thread  = None

    @staticmethod
    def init(bots: "list[BotBase]"):
        # Make it a static singleton
        if ApiServer.__init:
            ApiServer.__logger.warning('ApiServer already initialized')
            return

        api_port = BotConfig['Core']['api_port']

        ApiServer.__cmd = CommandProcessor(bots)

        ApiServer.__logger.info(f'Initializing server: 127.0.0.1:{api_port}')
        ApiServer.__server = UvicornServerPatch(uvicorn.Config(app=ApiServer.__app, host='127.0.0.1', port=api_port, log_level='debug'))

        ApiServer.__loop = asyncio.get_event_loop()
        ApiServer.__loop.create_task(ApiServer.__server.serve())

        # Thread needed for the async loop not to halt the rest of the bot
        ApiServer.__thread = threading.Thread(target=ApiServer.__loop.run_forever, daemon=True)
        ApiServer.__thread.start()

        ApiServer.__init = True


    @staticmethod
    def stop():
        ApiServer.__logger.info('Stopping api server...')
        #ApiServer._server.close()
        pass


    @staticmethod
    @__app.put('/request')
    async def _(data: fastapi.Request) -> dict:
        ApiServer.__logger.info(f'PUT /request {data}')

        try:
            data = await data.json()
            return ApiServer.__cmd.process_data(data)
        except Exception as e:
            warnings.warn(e, source=e)
            return Cmd.err('Something went wrong!')


    @staticmethod
    @__app.put('/ping')
    async def _(data: fastapi.Request) -> dict:
        ApiServer.__logger.info(f'PUT /ping {data}')
        return Cmd.ok('pong')
