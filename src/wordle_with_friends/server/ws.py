import logging

from aiohttp import web

from src.wordle_with_friends import serializer, config
from src.wordle_with_friends.server.manager import SessionManager

logger = logging.getLogger(__name__)


class WsServer:
    _app: web.Application
    _config: config.App
    _manager: SessionManager

    def __init__(self, app_config: config.App):
        self._config = app_config
        self._app = web.Application()
        self._app.add_routes(
            [
                web.get("/new", self.handle_new),
                web.get("/session/{session_id}", self.handle_session),
            ]
        )

        self._manager = SessionManager(app_config.empty_session_timeout_s)

    def run(self):
        web.run_app(self._app, port=9000)

    async def handle_new(self, _request: web.Request) -> web.StreamResponse:
        session = self._manager.create_new()
        logger.debug("creating session %s", session.id)
        return web.json_response(session, dumps=serializer.dumps)

    async def handle_session(self, request: web.Request) -> web.StreamResponse:
        session_id: str = request.match_info["session_id"]
        if session_id not in self._manager:
            raise web.HTTPNotFound()

        ws = web.WebSocketResponse()
        await ws.prepare(request)

        player_id = self._manager.add_player(session_id)
        logger.debug("%s joined session %s", player_id, session_id)

        try:
            async for msg in ws:
                logger.debug("received message %s", msg)
                await ws.send_str("pong")
        finally:
            self._manager.remove_player(session_id, player_id)

        return ws


def build() -> WsServer:
    return WsServer(config.App())
