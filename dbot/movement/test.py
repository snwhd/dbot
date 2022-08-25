#!/usr/bin/env python3

from dbot.movement.collision import (
    CollisionManager,
    CollisionState,
)

from dbot.movement.pathing import (
    Location,
    Pathing,
)


TEST_MAP = [
    [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ],
    [ 1, 0, 0, 0, 0, 0, 1, 0, 0, 1 ],
    [ 1, 0, 1, 1, 1, 0, 1, 1, 0, 1 ],
    [ 1, 0, 1, 1, 1, 0, 0, 1, 0, 1 ],
    [ 1, 0, 1, 1, 1, 0, 1, 1, 0, 1 ],
    [ 1, 0, 0, 1, 1, 0, 1, 0, 0, 1 ],
    [ 1, 0, 0, 0, 1, 0, 1, 0, 1, 1 ],
    [ 1, 0, 0, 0, 0, 0, 1, 0, 0, 1 ],
    [ 1, 0, 1, 0, 0, 0, 0, 0, 1, 1 ],
    [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ],
]

TEST_MAP = [
    [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ],
    [ 1, 0, 0, 0, 0, 0, 1, 0, 0, 1 ],
    [ 1, 0, 1, 1, 1, 0, 1, 1, 0, 1 ],
    [ 1, 0, 1, 1, 1, 0, 0, 1, 0, 1 ],
    [ 1, 0, 1, 1, 1, 0, 1, 1, 0, 1 ],
    [ 1, 0, 0, 1, 1, 2, 1, 0, 0, 1 ],
    [ 1, 0, 0, 2, 1, 0, 1, 0, 1, 1 ],
    [ 1, 0, 0, 0, 2, 0, 1, 0, 0, 1 ],
    [ 1, 0, 1, 2, 0, 0, 0, 0, 1, 1 ],
    [ 1, 2, 1, 1, 1, 1, 1, 1, 1, 1 ],
]


mapper = CollisionManager(None)
pather = Pathing(mapper)

cmap = mapper.get('test_map')

for y in range(len(TEST_MAP)):
    row = TEST_MAP[y]
    for x in range(len(row)):
        if row[x] == 0:
            cmap.set(x, y, False)
        elif row[x] == 1:
            cmap.set(x, y, True)

start = Location('test_map', (1, 1))
goal  = Location('test_map', (3, 8))
path = pather.path(start, goal)
print(path)


unknowns = pather.get_unknowns(start)
print(unknowns)
