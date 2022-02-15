import asyncio
from asyncio import Future
from typing import Dict

from src.wordle_with_friends import models


class SessionManager:
    sessions: Dict[str, models.Session]

    _closing_timeout_s: int
    _closing_tasks: Dict[str, Future]

    def __init__(self, closing_timeout_s: int):
        self.sessions = {}
        self._closing_timeout_s = closing_timeout_s
        self._closing_tasks = {}

    def __contains__(self, item: str) -> bool:
        return item in self.sessions

    def create_new(self) -> models.Session:
        session = models.Session.new()
        self.sessions[session.id] = session
        return session

    def add_player(self, session_id: str) -> str:
        self._cancel_session_closing(session_id)
        return self.sessions[session_id].add_player()

    def remove_player(self, session_id: str, player_id: str):
        empty = self.sessions[session_id].remove_player(player_id)
        if empty:
            self._mark_for_close(session_id)

    def _mark_for_close(self, session_id: str):
        """
        Prepares to close the session if no activity during the timeout.

        In the case that this ends up called multiple times, assume that the timeout should be
        restarted.

        :param session_id: session to close
        """
        self._cancel_session_closing(session_id)
        self._closing_tasks[session_id] = asyncio.create_task(
            self._wait_and_close(session_id, self._closing_timeout_s)
        )

    def _cancel_session_closing(self, session_id: str):
        previous_task = self._closing_tasks.pop(session_id, None)
        if previous_task is not None:
            previous_task.cancel()

    async def _wait_and_close(self, session_id: str, timeout: int):
        await asyncio.sleep(timeout)
        self.sessions.pop(session_id, None)

