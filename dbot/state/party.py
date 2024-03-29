from __future__ import annotations
from typing import (
    Dict,
    List,
    Optional,
)
import time    
import logging


# avoid cyclic import, but keep type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dbot.bot import BotCore


class Party:

    def __init__(
        self,
        bot: BotCore,
        players: List[str],
    ) -> None:
        assert len(players) <= 3
        self.players = list(players)
        self.target = list(players)
        self.bot = bot

    @property
    def leader(self) -> str:
        return self.players[0]

    @property
    def leader_is_me(self) -> bool:
        return self.leader == self.bot.name

    @property
    def position(self) -> int:
        return self.players.index(self.bot.name)

    @property
    def target_leader(self) -> str:
        return self.target[0]

    @property
    def target_leader_is_me(self) -> bool:
        return self.target_leader == self.bot.name

    @property
    def target_position(self) -> int:
        return self.target.index(self.bot.name)

    @property
    def is_complete(self) -> bool:
        return set(self.players) == set(self.target)

    @property
    def solo(self) -> bool:
        return len(self.players) == 1

    @property
    def in_party(self) -> bool:
        return len(self.players) > 1

    def identify_party(
        self,
        exclude: Optional[List[str]] = None,
    ) -> List[str]:
        friends = self.bot.logged_in_bots
        for to_remove in exclude or []:
            if to_remove in friends:
                friends.remove(to_remove)

        parties = [ friends[i:i+3] for i in range(0, len(friends), 3)]
        for party in parties:
            if self.bot.name in party:
                return party
        return [self.bot.name]

    def set_target(
        self,
        target: List[str],
    ) -> None:
        assert len(target) <= 3
        self.target = list(sorted(target))

    def update_party(
        self,
        players: List[str],
    ) -> None:
        logging.debug(f'new party: {players}')
        self.players = list(players)

    def player_left(
        self,
        player: str,
    ) -> None:
        if player in self.players:
            self.players.remove(player)
        if player in self.target:
            self.target.remove(player)
