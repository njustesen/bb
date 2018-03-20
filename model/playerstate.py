from enum import Enum


class PlayerState(Enum):
    READY = 1
    USED = 2
    ACTIVE = 3
    DOWN = 4
    STUNNED = 5
    KOD = 6
    BH = 7
    DEAD = 8