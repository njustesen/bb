from core.procedure import Procedure
from model import ActionType, Outcome, OutcomeType
import random


class CoinToss(Procedure):

    def __init__(self, game):
        super().__init__(game)
        self.away_won_toss = None

    def step(self, action):
        if self.away_won_toss is None:
            self.flip_coin(action)
            return False
        elif self.away_won_toss is not None:
            self.pick(action)
            return True

    def flip_coin(self, action):
        if action.action_type == ActionType.HEADS:
            if random.random() >= 0.5:
                self.away_won_toss = True
                self.game.report(Outcome(OutcomeType.HEADS_WON, team_home=False))
            else:
                self.away_won_toss = False
                self.game.report(Outcome(OutcomeType.HEADS_LOSS, team_home=False))
        elif action.action_type == ActionType.TAILS:
            if random.random() >= 0.5:
                self.away_won_toss = True
                self.game.report(Outcome(OutcomeType.TAILS_WON, team_home=False))
            else:
                self.away_won_toss = False
                self.game.report(Outcome(OutcomeType.TAILS_LOSS, team_home=False))

    def pick(self, action):
        if action.action_type == ActionType.KICK:
            self.game.state.kicking_team_home = False if self.away_won_toss else True
        elif action.action_type == ActionType.RECIEVE:
            self.game.state.kicking_team_home = True if self.away_won_toss else False
        if self.game.state.kicking_team_home:
            self.game.report(Outcome(OutcomeType.HOME_KICK))
        self.game.report(Outcome(OutcomeType.AWAY_KICK))
