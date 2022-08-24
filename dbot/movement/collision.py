from __future__ import annotations
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
)

import enum
import json
import logging
import pathlib
import random

from dbot.movement.pathfinding import Point


T = TypeVar('T', bound='CollisionMap')


class CollisionState(enum.Enum):

    bonk = 'bonk'
    nobonk = 'nobonk'
    unknown = 'unknown'
    transport = 'transport'


class CollisionManager:

    def __init__(
        self,
        directory: str,
    ) -> None:
        self.dir = pathlib.Path(directory)
        self.maps: Dict[str, CollisionMap] = {}

    def get(
        self,
        name: str,
    ) -> CollisionMap:
        if name in self.maps:
            return self.maps[name]
        filepath = self.dir / name
        if filepath.exists():
            with filepath.open() as f:
                cmap = CollisionMap.load(json.loads(f.read()))
            logging.info(f'loaded {filepath}.')
        else:
            logging.info(f'{filepath} doesnt exist, new map.')
            cmap = CollisionMap(name)
        self.maps[name] = cmap
        return cmap

    def save(self) -> None:
        for name, cmap in self.maps.items():
            filepath = self.dir / name
            with filepath.open('w') as f:
                f.write(json.dumps(cmap.save()))
            logging.info(f'saved {filepath}')


class CollisionMap:

    def __init__(
        self,
        name: str,
        cmap: Optional[Dict[int, Dict[int, bool]]] = None,
        transports: Optional[Dict[Tuple[int, int], str]] = None,
    ) -> None:
        # dicts make resizing easy
        self.transports = transports or {}
        self.map = cmap or {}
        self.name = name

    @classmethod
    def load(
        cls: Type[T],
        obj: Dict[str, Any],
    ) -> T:
        return cls(
            name=obj['name'],
            cmap=obj['map'],
            transports=obj['transports'],
        )

    def save(self) -> Any:
        return {
            'name': self.name,
            'map': self.map,
            'transports': self.transports,
        }

    def get(
        self,
        x: int,
        y: int,
    ) -> CollisionState:
        if x not in self.map or y not in self.map[x]:
            return CollisionState.unknown
        if self.map[x][y]:
            return CollisionState.bonk
        if (x, y) in self.transports:
            return CollisionState.transport
        return CollisionState.nobonk

    def set(
        self,
        x: int,
        y: int,
        collision: bool,
    ) -> None:
        if x not in self.map:
            self.map[x] = {}
        if y in self.map[x] and self.map[x][y] != collision:
            logging.warning(f'conflicting info at {self.name}({x}, {y})')
        self.map[x][y] = collision

    def set_transport(
        self,
        x: int,
        y: int,
        map_name: str,
        destination: Tuple[int, int],
    ) -> None:
        point = (x, y)
        transport = f'{map_name}{destination}'
        if point in self.transports and self.transports[point] != transport:
            logging.warning(f'conflicting transport at {self.name}{point}')
        self.transports[point] = transport

    def find_new(
        self,
        src: Point,
    ) -> Optional[List[Point]]:
        """ path the nearest unknown """
        return self.find_internal([src])

    def find_internal(
        self,
        path: List[Point],
    ) -> Optional[List[Point]]:
        current = path[-1]
        neighbors = self.neighbors(current)
        random.shuffle(neighbors)
        for point, collision in neighbors:
            if point in path:
                continue
            elif collision == CollisionState.unknown:
                # we hit one!
                path.append(point)
                return path
            elif collision == CollisionState.nobonk:
                path.append(point)
                result = self.find_internal(path)
                if result is not None:
                    return result
                path.pop()
        return None

    def neighbors(
        self,
        src: Point,
    ) -> List[Tuple[Point, CollisionState]]:
        return [
            (p, self.get(*p))
            for p in [
                (src[0] - 1, src[1]),
                (src[0] + 1, src[1]),
                (src[0], src[1] - 1),
                (src[0], src[1] + 1),
            ]
        ]
