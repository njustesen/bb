from core import Procedure
from model import ActionType, Outcome, OutcomeType
from exception import IllegalActionExcpetion


class PlaceBall(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.home = home

    def step(self, action):
        if not self.game.arena.is_team_side(action.pos_to, self.home):
            self.game.state.field.move_ball(action.pos_to, in_air=True)
            self.game.report(Outcome(OutcomeType.BALL_PLACED, pos=action.pos_to, team_home=self.home))
        else:
            raise IllegalActionExcpetion("Illegal position")
        return True
