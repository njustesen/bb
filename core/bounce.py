from core import Procedure
from model import Outcome, OutcomeType, DiceRoll, D8


class Bounce(Procedure):

    def __init__(self, game, home, kick=False):
        super().__init__(game)
        self.home = home  # With turn
        self.kick = kick

    def step(self, action):

        # Roll
        roll_scatter = DiceRoll([D8()])

        # Bounce
        x = 0
        y = 0
        if roll_scatter.get_sum() in [1, 4, 6]:
            x = -1
        if roll_scatter.get_sum() in [3, 5, 9]:
            x = 1
        if roll_scatter.get_sum() in [1, 2, 3]:
            y = -1
        if roll_scatter.get_sum() in [6, 7, 8]:
            y = 1

        self.game.state.field.ball_position[0] += x
        self.game.state.field.ball_position[1] += y
        if self.kick:
            # Kick - out of bounds
            if self.game.state.field.is_ball_out() or \
                    self.game.arena.is_team_side(self.game.state.field.ball_position, not self.home):
                self.game.report(Outcome(OutcomeType.TOUCHBACK, pos=self.game.state.field.ball_position,
                                         team_home=self.home, rolls=[roll_scatter]))
        else:
            # Out of bounds
            if self.game.state.field.is_ball_out():
                ThrowIn(self.game, self.home, self.game.state.field.ball_position)
                self.game.report(Outcome(OutcomeType.BALL_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                         team_home=self.home, rolls=[roll_scatter]))
            # On player -> Catch
            player_id = self.game.field.get_player_id_at(self.game.state.field.ball_position)
            if player_id is not None:
                Catch(self.game, self.home, player_id, self.game.state.field.ball_position)
                self.game.report(Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.game.state.field.ball_position,
                                         player_id=player_id, rolls=[roll_scatter]))

        self.game.report(Outcome(OutcomeType.BALL_ON_GROUND, pos=self.game.state.field.ball_position, team_home=self.home))
        return True