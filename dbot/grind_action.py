from __future__ import annotations
from typing import (
    Dict,
)
import enum
import logging
import time

# avoid cyclic import, but keep type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dbot.dbot import DBot

from dbot.action import Action
from dbot.uistate import UIScreen
from dbot.common import UIPositions


class GrindTarget(enum.Enum):
    none = 'none'
    field1 = 'field1'
    field2 = 'field2'
    cave1 = 'cave1'
    cave2 = 'cave2'
    gobble = 'gobble'
    bday_cave = 'bday cave'
    bday_rush = 'bday rush'


class GrindActionState(enum.Enum):

    # leader
    walking = 'waiting'
    returning = 'returning'

    # follower
    waiting = 'waiting'

    # all
    none = 'none'
    battle = 'battle'
    complete = 'complete'
    reloading = 'reloading'


class GrindAction(Action):

    def __init__(
        self,
        bot: DBot,
    ) -> None:
        super().__init__(bot)
        self.state = GrindActionState.none
        self.state_handlers = {
            GrindActionState.walking:  self.do_walking,
            GrindActionState.returning:  self.do_returning,
            GrindActionState.waiting:  self.do_waiting,
            GrindActionState.none:     self.do_none,
            GrindActionState.battle:   self.do_battle,
            GrindActionState.complete: self.do_complete,
            GrindActionState.reloading: self.do_reloading,
        }
        self.boss_defeated = False

    def set_state(
        self,
        new_state: GrindActionState,
    ) -> None:
        assert self.state != GrindActionState.complete, new_state
        if self.bot.party.target_leader_is_me:
            assert new_state != GrindActionState.waiting
        else:
            assert new_state not in {
                GrindActionState.walking,
                GrindActionState.returning,
            }, 'follower given leader state'
        self.state = new_state
        logging.debug(f'new action state: {self.state.value}')

    def step(self) -> None:
       self. state_handlers[self.state]()

    def do_walking(self) -> None:
        if self.bot.battle is not None:
            self.set_state(GrindActionState.battle)

    def do_returning(self) -> None:
        if self.bot.battle is not None:
            self.set_state(GrindActionState.battle)

    def do_waiting(self) -> None:
        if self.bot.battle is not None:
            self.set_state(GrindActionState.battle)

    def do_none(self) -> None:
        if self.bot.party.target_leader_is_me:
            if self.boss_defeated:
                self.set_state(GrindActionState.returning)
            else:
                self.set_state(GrindActionState.walking)
        else:
            self.set_state(GrindActionState.waiting)

    def do_battle(self) -> None:
        if self.bot.battle is not None:
            self.set_state(GrindActionState.none)

    def do_complete(self) -> None:
        """ boss is complete, walk to tp home """
        if self.bot.party.target_leader_is_me:
            ...
            # TODO: tell wiz to teleport
            # if self.boss_defeated:
            #     self.set_state(GrindActionState.returning)

    def do_reloading(self) -> None:
        """ each bot restocks their inv then parties up """
        ...

