from __future__ import annotations
from typing import (
    Optional,
)
import logging
import enum
import time

# avoid cyclic import, but keep type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dbot.dbot import DBot

import dbot.events as events


class BattleState(enum.Enum):

    not_in_battle = 'not in battle'
    waiting = 'waiting'
    ready = 'ready'


class BattleController:

    def __init__(
        self,
        bot: DBot,
    ) -> None:
        self.bot = bot
        self.next_round = 0.0
        self.round_start_delay = 3.0
        self.state = BattleState.waiting

        self.next_ability: Optional[int] = None
        self.next_target: Optional[int] = None

    def step(self) -> None:
        if self.state == BattleState.waiting:
            if time.time() > self.next_round:
                logging.debug('next round ready')
                self.state = BattleState.ready

    def check_event(
        self,
        e: events.GameEvent,
    ) -> bool:
        if isinstance(e, events.PlayOutBattleRound):
            seconds = float(e.duration) / 1000.0
            logging.debug(f'next round in {seconds} seconds')
            self.next_round = time.time() + seconds + 0.5
            return True
        return False

    def start(self) -> None:
        logging.debug('battle starting')
        self.next_round = time.time() + self.round_start_delay
        self.state = BattleState.waiting

    def leave(self) -> None:
        logging.debug('battle done')
        self.state = BattleState.not_in_battle


class SimpleClericController(BattleController):

    def __init__(
        self,
        bot: DBot,
    ) -> None:
        super().__init__(bot)

    def step(self) -> None:
        super().step()
        if self.state == BattleState.ready:
            # TODO: move this to base class for easier override?
            # TODO: selecting ability and target
            self.next_ability = 1
            self.next_target = 1

            assert self.next_ability is not None
            logging.debug(f'using {self.next_ability} on {self.next_target}')
            self.bot.socket.send_keypress(str(self.next_ability))
            self.state = BattleState.waiting

    def check_event(
        self,
        e: events.GameEvent,
    ) -> bool:
        super().check_event(e)
        if isinstance(e, events.PlayerUpdate):
            if (
                e.username == self.bot.name and
                e.key == 'selectedAbility' and
                e.value is not None
            ):
                assert self.next_target is not None
                self.bot.socket.send_keypress(str(self.next_target))
                self.next_ability = None
                self.next_target  = None
                return True
        return False


class SimpleWarriorController(BattleController):

    def __init__(
        self,
        bot: DBot,
    ) -> None:
        super().__init__(bot)

    def step(self) -> None:
        super().step()

    def check_event(
        self,
        e: events.GameEvent,
    ) -> bool:
        super().check_event(e)
        return False


class SimpleWizardController(BattleController):

    def __init__(
        self,
        bot: DBot,
    ) -> None:
        super().__init__(bot)

    def step(self) -> None:
        super().step()

    def check_event(
        self,
        e: events.GameEvent,
    ) -> bool:
        super().check_event(e)
        return False

