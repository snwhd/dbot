from __future__ import annotations
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
)

import enum
import json
import time
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
        directory: Optional[str],
    ) -> None:
        if directory is None:
            self.dir = None
        else:
            self.dir = pathlib.Path(directory)
        self.maps: Dict[str, CollisionMap] = {}

    def get(
        self,
        name: str,
    ) -> CollisionMap:
        if name in self.maps:
            return self.maps[name]
        if self.dir is not None:
            filepath = self.dir / name
            if filepath.exists():
                with filepath.open() as f:
                    cmap = CollisionMap.load(json.loads(f.read()))
                size = len(cmap.map)
                logging.info(f'loaded {filepath}. {size} Xs.')
                self.maps[name] = cmap
                return cmap
            logging.info(f'{filepath} doesnt exist, new map.')
        cmap = CollisionMap(name)
        self.maps[name] = cmap
        return cmap

    def save(self) -> None:
        if self.dir is None:
            return

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

        self.min: Optional[Tuple[int, int]] = None
        self.max: Optional[Tuple[int, int]] = None

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
        if x in self.transports and y in self.transports[x]:
            # it might be a transport (not in map)
            return CollisionState.transport
        if x in self.map and y in self.map[x]:
            # it's in the map, either collision or no
            if self.map[x][y]:
                return CollisionState.bonk
            return CollisionState.nobonk
        # otherwise, unexplored
        return CollisionState.unknown

    def set(
        self,
        ix: int,
        iy: int,
        collision: bool,
    ) -> None:
        x, y = str(ix), str(iy)
        if x in self.transports and y in self.transports[x]:
            logging.warning('overriding transport!?')

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
        if x in self.map and y in self.map[x]:
            logging.warning('transport overriding!?')

        transport = f'{map_name}{destination}'
        if (
            x in self.transports and
            y in self.transports[x] and 
            self.transports[x][y] != transport
        ):
            logging.warning(f'conflicting transport at {self.name}{(ix, iy)}')

        if x not in self.transports:
            self.transports[x] = {}
        self.transports[x][y] = transport

    def neighbors(
        self,
        src: Point,
    ) -> List[Tuple[Point, CollisionState]]:
        return [
            (p, self.get(*p))
            for p in [
                (src[0],     src[1] - 1),
                (src[0],     src[1] + 1),
                (src[0] - 1, src[1]),
                (src[0] + 1, src[1]),
            ]
        ]
