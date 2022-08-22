from __future__ import annotations
import logging
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

Point = Tuple[int, int]


# This is some really dumb path finding.
# TODO: parse the tile map and do it for real


class TownPathfinder:

    locations : Dict[str, Point] = {
        'bank_step': (46, 20),

        'mageshop_step':   (33, 22),
        'mageshop_inside': (100, 100),

        'armorshop_step':   (25, 22),
        'armorshop_inside': (100, 100),

        'inn_step':   (32, 16),
        'inn_inside': (100, 100),

        'overworld': (39, 0),
    }

    road_x = 39
    golb = (45, 19)

    @staticmethod
    def area(point: Point) -> str:
        x, y = point
        if 42 <= x <= 50 and 19 <= y <= 24:
            return 'bank'
        elif 37 <= x <= 41:
            return 'road'
        elif 31 <= x <= 36 and 15 <= y <= 17:
            return 'inn'
        elif 20 <= x <= 36 and 27 <= y <= 28:
            return 'shop road'
        else:
            raise ValueError(f'invalid area: {point}')

    @staticmethod
    def path_to(
        src: Point,
        dst: str,
    ) -> List[Point]:
        if dst == 'bank':
            return TownPathfinder.to_bank(src)
        if dst == 'inn':
            return TownPathfinder.to_inn(src)
        if dst == 'overworld':
            return TownPathfinder.to_overworld(src)
        if dst == 'road':
            return TownPathfinder.to_road(src)
        raise ValueError(f'invalid path destination: {dst}')
        

    @staticmethod
    def to_bank(src: Point) -> List[Point]:
        path = TownPathfinder.to_road(src)
        path.append(TownPathfinder.locations['bank_step'])
        return path

    @staticmethod
    def to_inn(src: Point) -> List[Point]:
        path = TownPathfinder.to_road(src)
        path.append(TownPathfinder.locations['inn_step'])
        return path

    @staticmethod
    def to_overworld(src: Point) -> List[Point]:
        path = TownPathfinder.to_road(src)
        path.append(TownPathfinder.locations['overworld'])
        return path

    @staticmethod
    def to_road(src: Point) -> List[Point]:
        path: List[Point] = []
        area = TownPathfinder.area(src)
        if area == 'bank':
            path.append((TownPathfinder.road_x, 20))
        elif area == 'inn':
            path.append((TownPathfinder.road_x, 16))
        elif area == 'shop road':
            path.append((TownPathfinder.road_x, 27))
        elif area == 'road':
            path.append((TownPathfinder.road_x, src[1]))
        else:
            raise ValueError(f'cannot path from {area} to overworld')
        return path
