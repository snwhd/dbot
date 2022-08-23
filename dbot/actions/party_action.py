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
from dbot.state.party import Party

from dbot.common.common import UIPositions
from dbot.movement.pathfinding import TownPathfinder


# TODO: move Party.target in PartyAction


class PartyActionState(enum.Enum):

    # leader
    waiting = 'waiting'
    selecting = 'selecting'

    # follower
    moving = 'moving'
    awaiting = 'awaiting'
    accepted = 'accepted'

    # all
    none = 'none'
    complete = 'complete'


class PartyAction(Action):

    def __init__(
        self,
        bot: BasicBot,
    ) -> None:
        super().__init__(bot)
        self.state = PartyActionState.none

        self.send_timeout = 2.5
        self.invites_sent: Dict[str, float] = {}
        self.selecting_since = 0.0

        self.state_handlers = {
            PartyActionState.waiting:   self.do_waiting,
            PartyActionState.selecting: self.do_selecting,
            PartyActionState.moving:    self.do_moving,
            PartyActionState.awaiting:  self.do_awaiting,
            PartyActionState.accepted:  self.do_accepted,
            PartyActionState.none:      self.do_none,
            PartyActionState.complete:  self.do_complete,
        }

    def set_state(
        self,
        new_state: PartyActionState,
    ) -> None:
        assert self.state != PartyActionState.complete, new_state
        if self.bot.party.target_leader_is_me:
            assert new_state not in {
                PartyActionState.moving,
                PartyActionState.awaiting,
                PartyActionState.accepted,
            }, 'leader given follower state'
        else:
            assert new_state not in {
                PartyActionState.waiting,
                PartyActionState.selecting,
            }, 'follower given leader state'
        self.state = new_state
        logging.debug(f'new action state: {self.state.value}')

    def step(self) -> bool:
        self.state_handlers[self.state]()
        return self.state == PartyActionState.complete

    def do_waiting(self) -> None:
        if self.bot.party.is_complete:
            self.set_state(PartyActionState.complete)
            self.bot.say('ready!', 'wsay') # TODO persist channel
            return

        now = time.time()
        for name in self.bot.party.target:
            if name != self.bot.name:
                player = self.bot.state.get_player(name)
                assert player is not None
                player_x = int(player['coords']['x'])
                player_y = int(player['coords']['y'])
                if (
                    abs(player_x - self.bot.me['coords']['x']) <= 1 and
                    abs(player_y - self.bot.me['coords']['y']) <= 1
                ):
                    sent_at = self.invites_sent.get(name)
                    if sent_at is None or (now - sent_at) > self.send_timeout:
                        logging.debug(f'sending invite to {name}')
                        self.invites_sent[name] = now
                        self.bot.click_at_tile(player_x, player_y)
                        self.set_state(PartyActionState.selecting)
                        self.selecting_since = now
                        break
                else:
                    logging.debug(f'{name} too far away ({player_x}, {player_y})')

    def do_selecting(self) -> None:
        now = time.time()
        if self.bot.ui.screen == UIScreen.player_select:
            if self.bot.ui.target in self.bot.party.target:
                self.bot.socket.send_click(*UIPositions.PARTY_INVITE)
                logging.debug(f'sent invite to {self.bot.ui.target}')
            else:
                logging.info(f'clicked wrong player ({self.bot.ui.target})')
                self.bot.socket.send_click(*UIPositions.PLAYER_SELECT_EXIT)
            self.set_state(PartyActionState.waiting)
        elif now - self.selecting_since > 0.5:
            logging.info('player select didnt pop up')
            self.set_state(PartyActionState.waiting)

    def do_moving(self) -> None:
        leader = self.bot.state.get_player(self.bot.party.target_leader)
        assert leader is not None
        me = self.bot.me
        if (
            self.bot.mover.target is None and
            abs(leader['coords']['x'] - me['coords']['x']) <= 1 and
            abs(leader['coords']['y'] - me['coords']['y']) <= 1
        ):
            self.set_state(PartyActionState.awaiting)
        elif self.bot.mover.target is None:
            # TODO: shouldn't hit this, but reset to target pos
            ...

    def do_awaiting(self) -> None:
        if self.bot.ui.screen == UIScreen.party_prompt:
            if self.bot.ui.source == self.bot.party.target_leader:
                self.bot.socket.send_click(*UIPositions.ACCEPT_INVITE)
                self.set_state(PartyActionState.accepted)
            else:
                self.bot.socket.send_click(*UIPositions.DECLINE_INVITE)
                self.set_state(PartyActionState.awaiting)

    def do_accepted(self) -> None:
        if self.bot.party.is_complete:
            self.set_state(PartyActionState.complete)

    def do_none(self) -> None:
        if self.bot.party.target_leader_is_me:
            src = (self.bot.me['coords']['x'], self.bot.me['coords']['y'])
            path = TownPathfinder.path_to(src, 'road')
            self.bot.goto(path)
            self.set_state(PartyActionState.waiting)
        else:
            self.set_state(PartyActionState.moving)
            leader = self.bot.state.get_player(self.bot.party.target_leader)
            assert leader is not None

            leader_src = (leader['coords']['x'], leader['coords']['y'])
            leader_path = TownPathfinder.path_to(leader_src, 'road')
            target_x, target_y = leader_path[-1]

            pos = self.bot.party.target_position
            if pos == 1:
                target_x -= 1
            else:
                target_x += 1

            # path to road first, just in case
            src = (self.bot.me['coords']['x'], self.bot.me['coords']['y'])
            path = TownPathfinder.path_to(src, 'road')
            path.append((target_x, target_y))
            self.bot.goto(path)

    def do_complete(self) -> None:
        pass
