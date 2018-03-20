from procs.procedure import Procedure
from procs.cointoss import CoinToss
from procs.weather import Weather


class Pregame(Procedure):

    def __init__(self, game):
        self.game = game
        self.procedures = []
        self.procedures.append(Weather(game))
        #procedures.append(GoldToPettyCash(game))
        #procedures.append(Inducements(game))
        self.procedures.append(CoinToss(game))
        super().__init__()

    def step(self, action):
        outcome, terminal = self.procedures[0].step(action)
        if outcome.terminal:
            self.procedures.pop()
        return outcome, len(self.procedures) > 0
