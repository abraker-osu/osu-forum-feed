import os
import platform
import asyncio
import socket

from typing import List, Optional, Sequence

import logging
import config as forumbot_config
import threading

import asyncio
import uvicorn
import fastapi

from core.botcore.console_framework.Cmd import Cmd
from core.botcore.console_framework.CommandProcessor import CommandProcessor



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

    async def startup(self: uvicorn.Server, sockets: Optional[List[socket.socket]] = None) -> None:
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

    app = fastapi.FastAPI()

    _init    = False
    _logger  = None
    _server  = None

    __loop   = None
    __thread = None

    @staticmethod
    def init():
        if ApiServer._init: # init guard
            ApiServer._logger.warn('ApiServer already initialized')
            return

        ApiServer._logger = logging.getLogger(__class__.__name__)

        ApiServer._logger.info('Initializing server: 127.0.0.1:44444')
        ApiServer._server = UvicornServerPatch(uvicorn.Config(app=ApiServer.app, host='127.0.0.1', port=forumbot_config.api_port, log_level='debug'))

        ApiServer.__loop = asyncio.get_event_loop()
        ApiServer.__loop.create_task(ApiServer._server.serve())

        ApiServer.__thread = threading.Thread(target=ApiServer.__loop.run_forever)
        ApiServer.__thread.setDaemon(True)
        ApiServer.__thread.start()

        ApiServer._init = True


    @staticmethod
    def stop():
        #ApiServer._server.close()
        pass


    @staticmethod
    @app.put('/request')
    async def handle_comment(data: fastapi.Request):
        try:
            data = await data.json()
            return CommandProcessor.process_data(data)
        except Exception as e:
            return Cmd.err(str(e))
