from core import Procedure, CoinToss, Weather


class Pregame(Procedure):

    def __init__(self, game):
        self.game.stack.push(CoinToss(self.game))
        # self.game.stack.push(Inducements(self.game, True))
        # self.game.stack.push(Inducements(self.game, False))
        # self.game.stack.push(GoldToPettyCash(self.game))
        self.game.stack.push(Weather(self.game))
        super().__init__(game)

    def step(self, action):
        return False
