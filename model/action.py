from enum import Enum


class ActionType(Enum):
    START_GAME = 1
    END_GAME = 2
    HEADS = 3
    TAILS = 4
    KICK = 5
    RECEIVE = 6
    PLACE_PLAYER = 7
    END_SETUP = 8
    PLACE_BALL = 9


class Action():

    def __init__(self, action_type, pos_from=None, pos_to=None, player_from_id=None, player_to_id=None):
        self.action_type = action_type
        self.pos_from = pos_from
        self.pos_to = pos_to
        self.player_from_id = player_from_id
        self.player_to_id = player_to_id

