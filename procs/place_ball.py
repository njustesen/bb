from procs.procedure import Procedure
from model.action import Action, ActionType
from model.outcome import Outcome, OutcomeType


class PlaceBall(Procedure):

    def __init__(self, game, home):
        self.game = game
        self.home = home
        super().__init__()

    def step(self, action):
        assert action in [ActionType.PLACE_BALL] and action.pos_to is not None
        if not self.game.arena.is_team_side(action.pos_to, self.home):
            self.game.state.field.move_ball(action.pos_to, in_air=True)
            return Outcome(OutcomeType.BALL_PLACED, pos=action.pos_to, team_home=self.home), True
        else:
            return Outcome(OutcomeType.NOT_ALLOWED, pos=action.pos_to, team_home=self.home), False
