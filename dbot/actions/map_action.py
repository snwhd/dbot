from __future__ import annotations
from typing import (
    Dict,
    Optional,
)
import enum
import logging
import time
import pathlib

# avoid cyclic import, but keep type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dbot.bot import BasicBot

from dbot.actions.action import Action
from dbot.movement.pathfinding import Point
from dbot.movement.collision import (
    CollisionManager,
    CollisionMap,
    CollisionState,
)


class MapActionState(enum.Enum):

    complete = 'complete'
    walking = 'walking'
    ready = 'ready'
    none = 'none'


class MapAction(Action):

    def __init__(
        self,
        bot: BasicBot,
    ) -> None:
        super().__init__(bot)
        self.state = MapActionState.none
        self.state_handlers = {
            MapActionState.complete: self.do_complete,
            MapActionState.walking:  self.do_walking,
            MapActionState.ready:    self.do_ready,
            MapActionState.none:     self.do_none,
        }
        self.directory = pathlib.Path('ignore') / f'{self.bot.name}_maps'
        self.directory.mkdir(parents=True, exist_ok=True)
        self.mapper = CollisionManager(str(self.directory))

        self.map: Optional[CollisionMap] = None
        self.current_town = ''
        self.current_destination: Optional[Point] = None

    def set_state(
        self,
        new_state: MapActionState,
    ) -> None:
        assert self.state != MapActionState.complete, new_state
        self.state = new_state

    def step(self) -> bool:
        self.state_handlers[self.state]()
        return self.state == MapActionState.complete

    def do_ready(self) -> None:
        # pick destination
        self.map = self.mapper.get(self.bot.state.map())
        path = self.map.find_new(self.bot.position)
        if path is None:
            self.set_state(MapActionState.complete)
            return

        self.bot.goto(path)
        self.set_state(MapActionState.walking)
        self.current_town = self.bot.state.map()
        self.current_destination = path[-1]

    def do_walking(self) -> None:
        if not self.bot.mover.still:
            return

        if self.bot.position == self.current_destination:
            # correct destination
            assert self.map is not None
            self.map.set(*self.bot.position, False)
        else:
            # we bonked
            assert self.current_destination is not None
            tx, ty = self.current_destination
            cx, cy = self.bot.position
            if abs(tx - cx) + abs(ty - cy) != 1:
                logging.error(f'mapping, bad destination')
                logging.error(f'  expected {self.current_destination}')
                logging.error(f'  got      {self.bot.position}')
                # TODO: this is probably a transport
            else:
                # we correctly bonked
                assert self.map is not None
                self.map.set(*self.current_destination, True)
        self.set_state(MapActionState.ready)

    def do_none(self) -> None:
        self.set_state(MapActionState.ready)

    def do_complete(self) -> None:
        ...

    def cleanup(self) -> None:
        self.mapper.save()
