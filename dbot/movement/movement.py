from __future__ import annotations
from typing import (
    List,
    Optional,
    Type,
    TypeVar,
)

import logging

# avoid cyclic import, but keep type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dbot.bot import BotCore

# network
import dbot.network.events as events

from dbot.common.common import (
    Direction,
)
from dbot.movement.pathfinding import (
    Point,
    TownPathfinder,
)


class MovementController:

    direction_keys = {
        Direction.up:    'w',
        Direction.down:  's',
        Direction.left:  'a',
        Direction.right: 'd',
    }

    def __init__(
        self,
        bot: BotCore,
    ) -> None:
        self.bot = bot
        self.state = {
            Direction.up: False,
            Direction.down: False,
            Direction.left: False,
            Direction.right: False,
        }

        self.queue: List[Point] = []
        self.target: Optional[Point] = None
        self.bonked = [False, False]

    @property
    def bonked_out(self) -> bool:
        if self.target is None:
            return False # TODO: idk

        tx, ty = self.target
        cx, cy = self.bot.position
        return any([
            all(self.bonked),            # bonk in both directions
            tx == cx and self.bonked[1], # correct x, bonked y
            ty == cy and self.bonked[0], # correct y, bonked x
        ])

    @property
    def still(self) -> bool:
        return self.target is None and len(self.queue) == 0

    #
    # movement basics
    #

    def move(
        self,
        direction: Direction,
        moving = True,
    ) -> None:
        key = self.direction_keys[direction]
        if moving and not self.state[direction]:
            if any(self.state.values()):
                logging.error(f'({direction.value}) - already moving!')
                logging.error(f'movement state: {self.state}')
                self.stop_moving()
            self.bot.socket.send_keydown(key)
            self.state[direction] = True
        if not moving and self.state[direction]:
            self.bot.socket.send_keyup(key)
            self.state[direction] = False

    def move_up(self) -> None:
        self.move(Direction.up)

    def move_down(self) -> None:
        self.move(Direction.down)

    def move_left(self) -> None:
        self.move(Direction.left)

    def move_right(self) -> None:
        self.move(Direction.right)

    def stop_up(self) -> None:
        self.move(Direction.up, False)

    def stop_down(self) -> None:
        self.move(Direction.down, False)

    def stop_left(self) -> None:
        self.move(Direction.left, False)

    def stop_right(self) -> None:
        self.move(Direction.right, False)

    def stop_moving(self) -> None:
        self.stop_up()
        self.stop_down()
        self.stop_left()
        self.stop_right()
        # self.bonked = [False, False]

    #
    # core loop
    #

    def step(self) -> None:
        if self.target is None:
            if not self.next_target():
                return
        assert self.target is not None

        tx, ty = self.target
        cx, cy = self.bot.position
        if (tx, ty) == (cx, cy):
            self.stop_moving()
            self.next_target()
            if self.target is None:
                # TODO: send chat message?
                logging.info('reached destination')
            else:
                logging.info('reached waypoint')
        elif self.bonked_out:
            logging.info('cannot reach destination')
            self.stop_moving()
            self.clear_goto()

        if self.target is None:
            # we just hit our destination or quit, no movement needed
            return

        # always move in y direction first, then x
        # unless bonked.
        if cy != ty and not self.bonked[1]:
            if cy > ty: self.move_up()
            else: self.move_down()
        elif cx != tx and not self.bonked[0]:
            if cx > tx: self.move_left()
            else: self.move_right()

        # note: Nothing else is needed because movement doesn't
        #       take effect until we get confirmation from the
        #       server anyway.

    def next_target(self) -> bool:
        self.bonked = [False, False]
        if len(self.queue) > 0:
            self.target = self.queue.pop(0)
            return True
        self.target = None
        return False

    def clear_goto(self) -> bool:
        self.stop_moving()
        self.bonked = [False, False]
        if self.target is not None or len(self.queue) > 0:
            self.target = None
            self.queue = []
            return True
        return False

    def goto(
        self,
        points: List[Point],
    ) -> None:
        self.queue = points

    #
    # event handling
    #

    def on_movePlayer(
        self,
        e: events.MovePlayer,
    ) -> None:
        player = self.bot.state.get_player(e.username)
        if player is None:
            return
        elif e.username != self.bot.name:
            return
        elif self.target is None:
            logging.warning('movePlayer for self, w/o target')
            self.stop_moving()
            return

        if e.direction in (Direction.down, Direction.up):
            diff = abs(player['coords']['y'] - self.target[1])
        else:
            diff = abs(player['coords']['x'] - self.target[0])

        near_threshold = 2
        if diff < near_threshold:
            self.move(e.direction, False)

    def on_bonk(
        self,
        e: events.Bonk,
    ) -> None:
        if self.state[Direction.up] or self.state[Direction.down]:
            self.bonked[1] = True
        else:
            self.bonked[0] = True
        self.stop_moving()
