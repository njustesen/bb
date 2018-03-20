from enum import Enum


class Action(Enum):
    START_GAME = 1
    END_GAME = 2
    HEADS = 3
    TAILS = 4
    KICK = 5
    RECEIVE = 6