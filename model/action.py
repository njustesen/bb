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
    START_MOVE = 10
    START_BLOCK = 11
    START_BLITZ = 12
    START_PASS = 13
    START_FOUL = 14
    START_HANDOFF = 15
    END_PLAYER_TURN = 16
    MOVE = 17
    BLOCK = 18
    BLITZ = 19
    PASS = 20
    FOUL = 21
    HANDOFF = 22
    USE_SKILL = 23
    USE_REROLL = 24
    END_TURN = 25
    SELECT_DIE = 26
    USE_APOTHECARY = 27
    USE_ROLL = 28
    USE_JUGGERNAUT = 29
    USE_WRESTLE = 30
    DONT_USE_WRESTLE = 31


class Action():

    def __init__(self, action_type, pos_from=None, pos_to=None, player_from_id=None, player_to_id=None, idx=0, team_home=True):
        self.action_type = action_type
        self.pos_from = pos_from
        self.pos_to = pos_to
        self.player_from_id = player_from_id
        self.player_to_id = player_to_id
        self.idx = idx
