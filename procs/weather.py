from procs.procedure import Procedure
from model.outcome import Outcome, OutcomeType
from model.gamestate import Weather as WeatherEnum
from model.dice import *


class Weather(Procedure):

    def __init__(self, game, kickoff=False):
        self.kickoff = kickoff
        super().__init__(game)

    def step(self, action):
        roll = DiceRoll([D6(), D6()])
        if roll.get_sum() == 2:
            self.game.state.weather = WeatherEnum.SWELTERING_HEAT
            self.game.report(Outcome(OutcomeType.WEATHER_SWELTERING_HEAT, rolls=[roll]))
        if roll.get_sum() == 3:
            self.game.state.weather = WeatherEnum.VERY_SUNNY
            self.game.report(Outcome(OutcomeType.WEATHER_VERY_SUNNY, rolls=[roll]))
        if 4 <= roll.get_sum() <= 10:
            self.game.state.weather = WeatherEnum.NICE
            if self.kickoff:
                self.game.state.gentle_gust = True
            self.game.report(Outcome(OutcomeType.WEATHER_NICE, rolls=[roll]))
        if roll.get_sum() == 11:
            self.game.state.weather = WeatherEnum.POURING_RAIN
            self.game.report(Outcome(OutcomeType.WEATHER_POURING_RAIN, rolls=[roll]))
        if roll.get_sum() == 12:
            self.game.state.weather = WeatherEnum.BLIZZARD
            self.game.report(Outcome(OutcomeType.WEATHER_BLIZZARD, rolls=[roll]))
        return True
