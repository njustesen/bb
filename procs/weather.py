from procs.procedure import Procedure
from model.action import Action
from model.outcome import Outcome
from model.outcome_type import OutcomeType
from model.dice import *
import random


class Weather(Procedure):

    def __init__(self, game):
        self.game = game
        super().__init__()

    def step(self, action):
        roll = DiceRoll([D6(), D6()])
        if roll.get_sum() == 2:
            return Outcome(OutcomeType.WEATHER_SWELTERING_HEAT, roll=roll), True
        if roll.get_sum() == 3:
            return Outcome(OutcomeType.WEATHER_VERY_SUNNY, roll=roll), True
        if 4 <= roll.get_sum() <= 10:
            return Outcome(OutcomeType.WEATHER_NICE, roll=roll), True
        if roll.get_sum() == 11:
            return Outcome(OutcomeType.WEATHER_POURING_RAIN, roll=roll), True
        if roll.get_sum() == 12:
            return Outcome(OutcomeType.WEATHER_BLIZZARD, roll=roll), True
