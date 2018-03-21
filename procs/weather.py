from procs.procedure import Procedure
from model.action import Action
from model.outcome import Outcome, OutcomeType
from model.gamestate import Weather as WeatherEnum
from model.dice import *
import random


class Weather(Procedure):

    def __init__(self, game, kickoff=False):
        self.game = game
        self.kickoff = kickoff
        super().__init__()

    def step(self, action):
        roll = DiceRoll([D6(), D6()])
        if roll.get_sum() == 2:
            self.game.state.weather = WeatherEnum.SWELTERING_HEAT
            return Outcome(OutcomeType.WEATHER_SWELTERING_HEAT, rolls=[roll]), True
        if roll.get_sum() == 3:
            self.game.state.weather = WeatherEnum.VERY_SUNNY
            return Outcome(OutcomeType.WEATHER_VERY_SUNNY, rolls=[roll]), True
        if 4 <= roll.get_sum() <= 10:
            self.game.state.weather = WeatherEnum.NICE
            if self.kickoff:
                self.game.state.gentle_gust = True
            return Outcome(OutcomeType.WEATHER_NICE, rolls=[roll]), True
        if roll.get_sum() == 11:
            self.game.state.weather = WeatherEnum.POURING_RAIN
            return Outcome(OutcomeType.WEATHER_POURING_RAIN, rolls=[roll]), True
        if roll.get_sum() == 12:
            self.game.state.weather = WeatherEnum.BLIZZARD
            return Outcome(OutcomeType.WEATHER_BLIZZARD, rolls=[roll]), True
