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

import dbot.network.events as events
from dbot.actions.action import Action
from dbot.movement.pathfinding import Point
from dbot.movement.collision import (
    CollisionManager,
    CollisionMap,
    CollisionState,
)


class MapActionState(enum.Enum):

    correcting = 'correcting'
    complete = 'complete'
    walking = 'walking'
    ready = 'ready'
    none = 'none'


class MapAction(Action):

    return_to_town = {
        'overworld': ((19, 29), (19, 32)),
        'inn':       ((22, 12), (22, 16)),
        'shop':      ((13, 16), (13, 20)),
        'armory':    ((16, 16), (16, 20)),
        'maika':     ((14, 11), (14, 15)),
        'clothier':  ((11, 16), (11, 20)),
        'clothier':  ((11, 16), (11, 20)),
    }

    def __init__(
        self,
        bot: BasicBot,
    ) -> None:
        super().__init__(bot)
        self.state = MapActionState.none
        self.state_handlers = {
            MapActionState.correcting: self.do_correcting,
            MapActionState.complete:   self.do_complete,
            MapActionState.walking:    self.do_walking,
            MapActionState.ready:      self.do_ready,
            MapActionState.none:       self.do_none,
        }
        self.directory = pathlib.Path('ignore') / f'{self.bot.name}_maps'
        self.directory.mkdir(parents=True, exist_ok=True)
        self.mapper = CollisionManager(str(self.directory))

        self.map: Optional[CollisionMap] = None
        self.current_destination: Optional[Point] = None

    def on_movePlayer(
        self,
        e: events.MovePlayer,
    ) -> None:
        player = self.bot.state.get_player(e.username)
        if player is not None:
            x = int(player['coords']['x'])
            y = int(player['coords']['y'])
            if self.map is not None:
                self.map.set(x, y, False)

    def on_other_player_bonked(
        self,
        map_name: str,
        point: Point,
    ) -> None:
        if self.map is not None and self.map.name == map_name:
            logging.debug(f'recording bonk from friend @ {point}')
            self.map.set(*point, True)

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
        # TODO: this is hardcoded to return to town
        path = None
        if self.bot.state.map() != 'town':
            map_name = self.bot.state.map()
            if map_name in self.return_to_town:
                logging.warning(f'returning from {map_name}')
                path = list(self.return_to_town[map_name])
                self.bot.goto(path)
                self.set_state(MapActionState.correcting)
                return
            else:
                logging.warning(f'stuck in {map_name}')
                self.set_state(MapActionState.complete)
                return

        # pick destination
        self.map = self.mapper.get(self.bot.state.map())
        path = self.map.find_new(self.bot.position)
        if path is None:
            if self.bot.is_bot_leader:
                self.bot.say(f'{self.bot.state.map()} map complete.')
            self.set_state(MapActionState.complete)
            return

        self.bot.goto(path)
        self.set_state(MapActionState.walking)
        self.current_destination = path[-1]

    def do_walking(self) -> None:
        if not self.bot.mover.still:
            return

        if self.bot.position == self.current_destination:
            # correct destination
            assert self.map is not None
            self.map.set(*self.bot.position, False)
        else:
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
                self.bot.say(f'dbots bonked at {self.map.name} {tx} {ty}')
        self.set_state(MapActionState.ready)

    def do_correcting(self) -> None:
        if self.bot.mover.still:
            self.set_state(MapActionState.ready)

    def do_none(self) -> None:
        self.set_state(MapActionState.ready)

    def do_complete(self) -> None:
        ...

    def cleanup(self) -> None:
        self.mapper.save()
