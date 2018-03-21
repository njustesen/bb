from procs.procedure import Procedure
from model.action import Action, ActionType
from model.outcome import Outcome, OutcomeType
import random


class CoinToss(Procedure):

    def __init__(self, game):
        self.game = game
        self.away_won_toss = None
        super().__init__()

    def step(self, action):
        if self.away_won_toss is None:
            assert action in [ActionType.HEADS, ActionType.TAILS]
            return self.flip_coin(), False
        elif self.away_won_toss is not None:
            assert action in [ActionType.KICK, ActionType.RECEIVE]
            return self.pick(action), True

    def flip_coin(self, action):
        if action.action_type == ActionType.HEADS:
            if random.random() >= 0.5:
                self.away_won_toss = True
                return Outcome(OutcomeType.HEADS_WON)
            else:
                self.away_won_toss = False
                return Outcome(OutcomeType.HEADS_LOSS)
        elif action.action_type == ActionType.TAILS:
            if random.random() >= 0.5:
                self.away_won_toss = True
                return Outcome(OutcomeType.TAILS_WON)
            else:
                self.away_won_toss = False
                return Outcome(OutcomeType.TAILS_LOSS)

    def pick(self, action):
        if action.action_type == ActionType.KICK:
            self.game.state.kicking_team_home = False if self.away_won_toss else True
        elif action.action_type == ActionType.RECIEVE:
            self.game.state.kicking_team_home = True if self.away_won_toss else False
        if self.game.state.kicking_team_home:
            return Outcome(OutcomeType.HOME_KICK)
        return Outcome(OutcomeType.AWAY_KICK)
