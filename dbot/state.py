from typing import (
    Any,
    Dict,
    Optional,
    Set,
)


Player = Dict[str, Any]


class GameState:

    def __init__(self) -> None:
        self.players: Dict[str, Player] = {}
        self.players_in_map: Set[str] = set()
        self.vars : Dict[str, Any] = {}

        self.last_map : Optional[str] = None
        self.current_map : Optional[str] = None

    def left_map(self) -> None:
        self.last_map = self.current_map
        self.current_map = None

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

