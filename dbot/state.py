from typing import (
    Any,
    Dict,
    Optional,
    Set,
)

import logging

from dbot.common import (
    Player,
    PlayerData,
)


class GameState:

    def __init__(self) -> None:
        self.players: Dict[str, Player] = {}
        self.players_in_map: Set[str] = set()
        self.vars : Dict[str, Any] = {}

        self.last_map : Optional[str] = None
        self.current_map : Optional[str] = None

    def left_map(
        self,
        username: Optional[str] = None,
    ) -> None:
        if username is None:
            # self left map
            self.last_map = self.current_map
            self.current_map = None
        elif username in self.players_in_map:
            self.players_in_map.remove(username)

    def join_map(
        self,
        map_name: str,
    ) -> None:
        assert self.current_map is None
        self.current_map = map_name

    def map(self) -> str:
        return self.current_map or self.last_map or '<unknown>'

    def get_player(
        self,
        name: str,
    ) -> Optional[Player]:
        return self.players.get(name)

    def add_player(
        self,
        player: PlayerData,
    ) -> None:
        username = player.username
        if username in self.players:
            logging.warning(f'{username} already logged in?')
        self.players[username] = {
            'username': username,
        }
