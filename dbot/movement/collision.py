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
CMap = Dict[str, Dict[str, bool]]
TransportMap = Dict[str, Dict[str, str]]


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
            size = len(cmap.map)
            logging.info(f'loaded {filepath}. {size} Xs.')
        else:
            logging.info(f'{filepath} doesnt exist, new map.')
            cmap = CollisionMap(name)
        self.maps[name] = cmap
        return cmap

    def save(self) -> None:
        for name, cmap in self.maps.items():
            filepath = self.dir / name
            with filepath.open('w') as f:
                f.write(json.dumps(cmap.save(), indent=2))
            logging.info(f'saved {filepath}')


class CollisionMap:

    def __init__(
        self,
        name: str,
        cmap: Optional[CMap] = None,
        transports: Optional[TransportMap] = None,
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
        ix: int,
        iy: int,
    ) -> CollisionState:
        x, y = str(ix), str(iy)
        if x not in self.map or y not in self.map[x]:
            return CollisionState.unknown
        if self.map[x][y]:
            return CollisionState.bonk
        if x in self.transports and y in self.transports[x]:
            return CollisionState.transport
        return CollisionState.nobonk

    def set(
        self,
        ix: int,
        iy: int,
        collision: bool,
    ) -> None:
        x, y = str(ix), str(iy)
        if x not in self.map:
            self.map[x] = {}
        if y in self.map[x] and self.map[x][y] != collision:
            logging.warning(f'conflicting info at {self.name}({x}, {y})')
        self.map[x][y] = collision

    def set_transport(
        self,
        ix: int,
        iy: int,
        map_name: str,
        destination: Tuple[int, int],
    ) -> None:
        x, y = str(ix), str(iy)
        point = (ix, iy)
        transport = f'{map_name}{destination}'
        if (
            x in self.transports and
            y in self.transports[x] and 
            self.transports[x][y] != transport
        ):
            logging.warning(f'conflicting transport at {self.name}{point}')

        if x not in self.transports:
            self.transports[x] = {}
        self.transports[x][y] = transport

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
