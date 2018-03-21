from enum import Enum


class OutcomeType(Enum):
    HEADS_WON = 1
    HEADS_LOSS = 2
    WEATHER_SWELTERING_HEAT = 3
    WEATHER_VERY_SUNNY = 4
    WEATHER_NICE = 5
    WEATHER_POURING_RAIN = 6
    WEATHER_BLIZZARD = 7
    NOT_ALLOWED = 8
    PLAYER_PLACED = 9
    ILLEGAL_SETUP_NUM = 10
    ILLEGAL_SETUP_SCRIMMAGE = 11
    ILLEGAL_SETUP_WINGS = 12
    BALL_PLACED = 13
    KICKOFF_GET_THE_REF = 14
    KICKOFF_RIOT = 15
    KICKOFF_PERFECT_DEFENSE = 16
    KICKOFF_HIGH_KICK = 17
    KICKOFF_CHEERING_FANS = 18
    KICKOFF_CHANGING_WHEATHER = 19
    KICKOFF_BRILLIANT_COACHING = 20
    KICKOFF_QUICK_SNAP = 21
    KICKOFF_BLITZ = 22
    KICKOFF_THROW_A_ROCK = 23
    KICKOFF_PITCH_INVASION = 24
    GET_THE_REF = 25
    RIOT = 26
    HIGH_KICK = 27
    CHEERING_FANS = 28
    BRILLIANT_COACHING = 29
    THROW_A_ROCK = 30
    PITCH_INVASION = 31
    PITCH_INVASION_ROLL = 32
    NOTHING = 33
    KICK_IN_BOUNDS = 34
    KICK_OUT_OF_BOUNDS = 35
    BALL_HIT_GROUND = 36
    BALL_HIT_PLAYER = 37
    SETUP_DONE = 38


class Outcome:

    def __init__(self, outcome_type, pos=None, player_id=-1, rolls=[], team_home=None, n=0):
        self.outcome_type = outcome_type
        self.pos = pos
        self.player_id = player_id
        self.rolls = rolls
        self.team_home = team_home
        self.n = n
