from __future__ import annotations
from typing import (
    Dict,
    List,
    Optional,
)
import enum
import logging
import time
import pathlib
import random

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
from dbot.movement.pathing import (
    Location,
    Pathing,
)


REFRESH_THRESHOLD = 10
DISTANCE_THRESHOLD = 5


class MapActionState(enum.Enum):

    correcting = 'correcting'
    complete = 'complete'
    walking = 'walking'
    ready = 'ready'
    none = 'none'


class MapAction(Action):

    def __init__(
        self,
        bot: BasicBot,
        focus_map: Optional[str] = None,
        frequent_saves = False,
    ) -> None:
        super().__init__(bot)
        self.focus_map = focus_map
        self.frequent_saves = frequent_saves
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

        self.current_destination: Optional[Location] = None
        self.queue: List[Point] = []

    @property
    def map(self) -> Optional[CollisionMap]:
        if self.current_destination is not None:
            return self.mapper.get(self.current_destination.map)
        return None

    def resolved(
        self,
        point: Point,
    ) -> None:
        if point in self.queue:
            logging.debug(f'removed {point} from queue')
            self.queue.remove(point)
        dest = self.current_destination
        if dest is not None and dest.point == point:
            self.current_destination = None
            self.bot.mover.stop_moving()
            self.dest = None

        if self.frequent_saves:
            self.mapper.save()

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
                self.resolved((x, y))

    def on_other_player_bonked(
        self,
        map_name: str,
        point: Point,
    ) -> None:
        cmap = self.mapper.get(map_name)
        if cmap is not None:
            logging.debug(f'recording bonk from friend @ {point}')
            cmap.set(*point, True)
            self.resolved(point)

    def on_player_transported(
        self,
        from_map: str,
        from_point: Point,
        to_map: str,
        to_point: Point,
    ) -> None:
        cmap = self.mapper.get(from_map)
        if cmap is not None:
            f = f'{from_map}{from_point}'
            t = f'{to_map}{to_point}'
            logging.debug(f'recording transport {f} -> {t}')
            cmap.set_transport(
                *from_point,
                to_map,
                to_point,
            )
            self.resolved(from_point)

    def set_state(
        self,
        new_state: MapActionState,
    ) -> None:
        assert self.state != MapActionState.complete, new_state
        self.state = new_state

    def step(self) -> bool:
        self.state_handlers[self.state]()
        return self.state == MapActionState.complete

    def condense(
        self,
        path: List[Point],
    ) -> List[Point]:
        condensed: List[Point] = []
        if len(path) < 3:
            return path

        start = self.bot.position
        prev = start
        old_delta = (-2, -2) # an invalid delta

        for point in path:
            delta = (point[0] - prev[0], point[1] - prev[1])
            assert abs(delta[0]) + abs(delta[1]) <= 1, (point, prev, path)
            if delta != old_delta:
                condensed.append(prev)
                old_delta = delta
            if point == path[-1]:
                condensed.append(point)
            prev = point

        if len(condensed) > 1:
            # TODO: remove this when sure condense isn't borked
            prev = condensed[0]
            for p in condensed[1:]:
                delta = (p[0] - prev[0], p[1] - prev[1])
                if abs(delta[0]) > 0 and abs(delta[1]) > 0:
                    logging.error(f'condense failed on {path} -> {condensed}')
                    return path
                prev = p

        assert condensed[-1] == path[-1], f'condensed {start} - {path} to {condensed}'
        return condensed


    def do_ready(self) -> None:
        path = None
        pathing = Pathing(self.mapper)
        current_map = self.bot.state.map()
        if self.focus_map is not None and current_map != self.focus_map:
            path = pathing.path_to_map(
                Location(self.focus_map, self.bot.position),
                self.focus_map,
            )
            if path is not None:
                # TODO: This will fail if we try to path through
                #       multiple maps.
                self.bot.goto(path)
                self.set_state(MapActionState.correcting)
            else:
                self.bot.say(f'I\'m stuck in {current_map}', 'wsay')
                self.set_state(MapActionState.complete)
            return

        # pick a destination
        pick_random = False
        if len(self.queue) < REFRESH_THRESHOLD:
            # refresh the queue
            self.queue = pathing.get_unknowns(Location(
                current_map,
                self.bot.position,
            ))
            logging.debug(f'refreshed queue: {self.queue}')

            # by having a REFRESH_THRESHOLD > nbots, and picking a random
            # point every time it refreshes, we avoid bots following the
            # same path with a small queue
            pick_random = True

        if len(self.queue) == 0:
            # still empty? we cleared the map
            self.bot.say(f'{current_map} map complete.', 'wsay')
            self.set_state(MapActionState.complete)
            return

        def distance_to(point: Point) -> int:
            x, y = self.bot.position
            return abs(point[0] - x) + abs(point[1] - y)

        def nearest() -> Point:
            nearest = self.queue[0], distance_to(self.queue[0])
            for point in self.queue[1:]:
                distance = distance_to(point)
                if distance < nearest[1]:
                    nearest = point, distance
            return nearest[0]

        next_point = random.choice(self.queue) if pick_random else nearest()

        if not pick_random and distance_to(next_point) > DISTANCE_THRESHOLD:
            self.queue = pathing.get_unknowns(Location(
                current_map,
                self.bot.position,
            ))
            if len(self.queue) == 0:
                # can this edge case actually be hit?
                self.bot.say(f'{current_map} map complete.', 'wsay')
                self.set_state(MapActionState.complete)
                return
            next_point = nearest()

        self.current_destination = Location(
            current_map,
            next_point,
        )

        path = pathing.path(
            Location(current_map, self.bot.position),
            self.current_destination,
        )
        if path is not None:
            logging.debug(f'dest: {self.current_destination} ({path})')
            self.bot.goto(self.condense(path))
            self.set_state(MapActionState.walking)
        else:
            # we should never hit this, but just ignore
            self.queue.remove(next_point)


    def do_walking(self) -> None:
        if not self.bot.mover.still:
            # still walking
            return

        if self.current_destination is None:
            # someone else resovled our target
            self.set_state(MapActionState.ready)
            return

        end_location = Location(
            self.bot.state.map(),
            self.bot.position,
        )

        if end_location == self.current_destination:
            # correct destination
            assert self.map is not None
            self.map.set(*end_location.point, False)
            self.resolved(end_location.point)
        elif self.map is not None:
            # incorrect destination, transported or bonked
            tx, ty = self.current_destination.point
            cx, cy = end_location.point

            if abs(tx - cx) + abs(ty - cy) != 1:
                # moved by more than 1 from expected dest, must be transport
                # because destination is the only unknown tile, we can trust
                # that it is the transport tile.
                expected_map = self.current_destination.map
                actual_map = end_location.map
                if expected_map == actual_map:
                    logging.error('TODO: transport within map?')
                    self.set_state(MapActionState.ready)
                    return

                self.on_player_transported(
                    expected_map,
                    (tx, ty),
                    actual_map,
                    (cx, cy),
                )
                self.bot.say(''.join([
                    'dbots transported at ',
                    f'{expected_map} {tx} {ty} to ',
                    f'{actual_map} {cx} {cy}',
                ]), 'wsay')
            else:
                # we correctly bonked
                self.map.set(*self.current_destination.point, True)
                self.bot.say(
                    f'dbots bonked at {self.current_destination.map} {tx} {ty}',
                    'wsay',
                )
                self.resolved(self.current_destination.point)
        else:
            logging.warning('self.map is None in walking state')
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
