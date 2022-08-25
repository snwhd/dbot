from __future__ import annotations
from typing import (
    Dict,
    List,
    Optional,
    Set,
    Tuple,
)

import heapq
import math
import logging

from dbot.movement.collision import (
    CollisionManager,
    CollisionMap,
    CollisionState,
)


Point = Tuple[int, int]


class Location:

    def __init__(
        self,
        map_name: str,
        point: Point,
    ) -> None:
        self.map = map_name
        self.point = point

    def __eq__(
        self,
        other: object,
    ) -> bool:
        if isinstance(other, Location):
            return other.map == self.map and other.point == self.point
        elif isinstance(other, tuple) and len(other) == 2:
            map_name, point = other
            return all ([
                isinstance(map_name, str),
                isinstance(point, tuple),
                map_name == self.map,
                point == self.point,
            ])
        return False

    def __str__(self) -> str:
        return f'{self.map}{self.point}'


class Pathing:

    def __init__(
        self,
        collider: CollisionManager,
    ) -> None:
        self.collider = collider

    def get_unknowns(
        self,
        start: Location,
    ) -> List[Point]:
        cmap = self.collider.get(start.map)
        unknowns: Set[Point] = set()
        done: Set[Point] = set()
        todo = { start.point }

        while len(todo) > 0:
            current = todo.pop()
            done.add(current)

            for point, state in cmap.neighbors(current):
                if point in done or point in todo:
                    continue
                elif state == CollisionState.nobonk:
                    todo.add(point)
                elif state == CollisionState.unknown:
                    unknowns.add(point)
                    done.add(point)

        return list(unknowns)

    def path_to_map(
        self,
        start: Location,
        goal: str,
    ) -> Optional[List[Point]]:
        # TODO: finish this, and do it better
        current_map = start.map
        if goal == 'town':
            if current_map == 'overworld':
                return [(19, 29), (19, 32)]
            elif current_map == 'inn':
                return [(22, 12), (22, 16)]
            elif current_map == 'shop':
                return [(13, 16), (13, 20)]
            elif current_map == 'armory':
                return [(16, 16), (16, 20)]
            elif current_map == 'maika':
                return [(14, 11), (14, 15)]
            elif current_map == 'clothier':
                return [(11, 16), (11, 20)]
            elif current_map == 'clothier':
                return [(11, 16), (11, 20)]
        elif goal == 'overworld':
            if current_map == 'town':
                return self.path(start, Location('town', (39, 6)))
        return None

    def path(
        self,
        start: Location,
        goal: Location,
    ) -> Optional[List[Point]]:
        assert start.map == goal.map, 'TODO: map to map pathing'
        cmap = self.collider.get(start.map)

        if cmap.get(*start.point) == CollisionState.unknown:
            logging.debug('manually adding start location as nobonk')
            cmap.set(*start.point, False)

        open_set: List[Tuple[float, Point]]  = []
        came_from: Dict[Point, Point] = {}

        g_scores: Dict[Point, float] = {
            start.point: 0.0,
        }
        f_scores: Dict[Point, float] = {
            start.point: 0.0,
        }

        def push(point: Point):
            f = f_scores.get(point, math.inf)
            heapq.heappush(open_set, (f, point))

        push(start.point)

        while len(open_set) > 0:
            g, current = heapq.heappop(open_set)
            if current == goal.point:
                # hit the goal! build path
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                assert path[-1] == start.point
                return list(reversed(path))

            if cmap.get(*current) != CollisionState.nobonk:
                # anything can be a destination, but we will conly
                # continue the search if it's an open spot
                # Note: this has to change when supporting multi-map
                continue

            for neighbor, state in cmap.neighbors(current):
                # +1 for now because each tile is equally weighted
                tmpg = g_scores.get(current, math.inf) + 1
                if tmpg < g_scores.get(neighbor, math.inf):
                    # a better path
                    came_from[neighbor] = current
                    g_scores[neighbor] = tmpg
                    f_scores[neighbor] = tmpg + self.h(start.point, neighbor)
                    if neighbor not in open_set:
                        push(neighbor)

        logging.info(f'no path to {goal}')
        return None

    def h(
        self,
        start: Point,
        goal: Point,
    ) -> float:
        return abs(goal[0] - start[0]) + abs(goal[1] - start[1])
