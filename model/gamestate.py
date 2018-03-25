from model import *
from enum import Enum
import random
import numpy as np


class Dugout:

    def __init__(self):
        self.reserves = []
        self.kod = []
        self.casualties = []


class TeamState:

    def __init__(self, team):
        self.bribes = 0
        self.babes = 0
        self.apothecary_available = team.apothecary
        self.player_states = {player.player_id: PlayerState.READY for player in team.players}
        self.injuries = {}
        self.score = 0
        self.turn = 0
        self.apothecary = team.apothecary
        self.rerolls_start = team.rerolls
        self.rerolls = team.rerolls
        self.ass_coaches = team.ass_coaches
        self.cheerleaders = team.cheerleaders
        self.fame = 0
        self.reroll_used = False

    def reset_half(self):
        self.reroll_used = False
        self.rerolls = self.rerolls_start
        self.turn = 0

    def reset_turn(self):
        self.reroll_used = False

    def use_reroll(self):
        self.rerolls -= 1
        self.reroll_used = True


class WeatherType(Enum):
    SWELTERING_HEAT = 1
    VERY_SUNNY = 2
    NICE = 3
    POURING_RAIN = 4
    BLIZZARD = 5


class GameState:

    def __init__(self, game):
        self.half = 1
        self.kicking_team = None
        self.field = Field(game)
        self.home_dugout = Dugout()
        self.away_dugout = Dugout()
        self.home_state = TeamState(game.home)
        self.away_state = TeamState(game.away)
        self.weather = None
        self.gentle_gust = False
        self.team_turn = None

    def reset_turn(self, home):
        self.team_turn = None
        self.get_team_state(home).reset_turn()

    def reset_kickoff(self):
        self.team_turn = None
        self.home_state.reset_turn()
        self.away_state.reset_turn()

    def reset_half(self, home):
        self.team_turn = None
        self.get_team_state(home).reset_half()

    def get_player_state(self, player_id, home):
        return self.get_team_state(home).player_states[player_id]

    def set_player_state(self, player_id, home, player_state):
        self.get_team_state(home).player_states[player_id] = player_state

    def get_team_state(self, home):
        return self.home_state if home else self.away_state

    def get_dugout(self, home):
        return self.home_dugout if home else self.away_dugout

    def knock_out(self, home, player_id):
        self.get_team_state(home).player_states[player_id] = PlayerState.KOD
        self.field.remove(player_id)
        self.get_dugout(home).kod.append(player_id)

    def badly_hurt(self, home, player_id):
        self.get_team_state(home).player_states[player_id] = PlayerState.BH
        self.field.remove(player_id)
        self.get_dugout(home).casualties.append(player_id)

    def can_use_reroll(self, home):
        return not self.get_team_state(home).reroll_used and self.get_team_state(home).rerolls > 0

    def use_reroll(self, home):
        self.get_team_state(home).reroll_used = True
        self.get_team_state(home).rerolls -= 1
