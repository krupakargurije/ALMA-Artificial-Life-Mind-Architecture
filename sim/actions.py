"""Fixed action set with opaque integer IDs for ALC.

Strict rule: Brain chooses only from opaque integer IDs.
World rules map these integers to simulation behavior.
"""

from typing import Dict, Tuple

# Action IDs
WAIT = 0
MOVE_N = 1
MOVE_S = 2
MOVE_E = 3
MOVE_W = 4
PICK_UP = 5
DROP = 6
USE_ON_FACING = 7
EAT = 8
DRINK = 9
DIG = 10
EMIT_SIGNAL_0 = 11
EMIT_SIGNAL_1 = 12
EMIT_SIGNAL_2 = 13
EMIT_SIGNAL_3 = 14

TOTAL_ACTIONS = 15
ALL_ACTIONS = tuple(range(TOTAL_ACTIONS))

# Direction Vectors: (dx, dy)
# In 2D grid: y=0 is North/top, y=height-1 is South/bottom.
DIR_NORTH: Tuple[int, int] = (0, -1)
DIR_SOUTH: Tuple[int, int] = (0, 1)
DIR_EAST: Tuple[int, int] = (1, 0)
DIR_WEST: Tuple[int, int] = (-1, 0)

MOVE_ACTION_DIRS: Dict[int, Tuple[int, int]] = {
    MOVE_N: DIR_NORTH,
    MOVE_S: DIR_SOUTH,
    MOVE_E: DIR_EAST,
    MOVE_W: DIR_WEST,
}

SIGNAL_ACTIONS = (EMIT_SIGNAL_0, EMIT_SIGNAL_1, EMIT_SIGNAL_2, EMIT_SIGNAL_3)
