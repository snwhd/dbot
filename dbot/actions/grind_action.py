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
    from dbot.bot import BasicBot

from dbot.actions.action import Action
from dbot.state.uistate import UIScreen

from dbot.common.common import UIPositions
from dbot.movement.pathfinding import (
    OverworldPathfinder,
    TownPathfinder,
)


class GrindTarget(enum.Enum):
    field_west = 'field_west'
    field_east = 'field_east'
    cave1 = 'cave1'
    cave2 = 'cave2'
    gobble = 'gobble'
    bday_cave = 'bday cave'
    bday_rush = 'bday rush'


class GrindActionState(enum.Enum):

    # leader
    walking = 'walking'
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
        bot: BasicBot,
        target: GrindTarget,
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
        self.target = target

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

    def at_target(self) -> bool:
        if self.target == GrindTarget.field_west:
            return self.bot.state.map() == 'overworld'
        else:
            raise NotImplementedError('only overworld grind.')

    def step(self) -> bool:
        self. state_handlers[self.state]()
        return self.state == GrindActionState.complete

    def do_walking(self) -> None:
        if self.bot.battle is not None:
            self.set_state(GrindActionState.battle)
            return
        elif self.bot.party.in_party and not self.bot.party.leader_is_me:
            # can't control the party
            return
        elif self.bot.mover.target is not None:
            # already in motion
            return

        if self.at_target():
            # circle
            path = OverworldPathfinder.circle_field_west()
            self.bot.goto(path)
        elif self.bot.state.map() == 'town':
            src = (self.bot.me['coords']['x'], self.bot.me['coords']['y'])
            path = TownPathfinder.path_to(src, 'overworld')
            self.bot.goto(path)
        else:
            # TODO: pathfind from more than just town
            logging.warning(f"can't pathfind from {self.bot.state.map}")
            return

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

