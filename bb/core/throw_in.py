from core import Procedure, Catch, Bounce
from model import Outcome, OutcomeType, DiceRoll, D3, D6


class ThrowIn(Procedure):

    def __init__(self, game, home, pos):
        super().__init__(game)
        self.home = home  # With turn
        self.pos = pos

    def step(self, action):

        # Roll
        roll_scatter = DiceRoll([D3()])
        roll_distance = DiceRoll([D6(), D6()])

        # Scatter
        x = 0
        y = 0
        if self.pos[0] < 0:  # Above
            y = -1
        elif self.pos[0] > len(self.game.arena.board[0]):  # Below
            y = 1
        elif self.pos[1] < 0:  # Right
            x = 1
        elif self.pos[1] < len(self.game.arena.board[1]):  # Left
            x = -1

        if roll_scatter.get_sum() == 1:
            if x == 0:
                x = -1
            elif y == 0:
                y = 1
        if roll_scatter.get_sum() == 3:
            if x == 0:
                x = 1
            elif y == 0:
                y = -1

        for i in range(roll_distance.get_sum()):
            self.game.state.field.ball_position[0] += x
            self.game.state.field.ball_position[1] += y
            if self.game.state.field.is_ball_out():
                # Move ball back
                self.game.state.field.ball_position[0] -= x
                self.game.state.field.ball_position[1] -= y
                ThrowIn(self.game, self.home, self.game.state.field.ball_position)
                self.game.report(Outcome(OutcomeType.BALL_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                         team_home=self.home, rolls=[roll_scatter, roll_distance]))
            else:

                # On player -> Catch
                player_id = self.game.field.get_player_id_at(self.game.state.field.ball_position)
                if player_id is not None:
                    Catch(self.game, self.home, player_id, self.game.state.field.ball_position)
                    self.game.report(Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.game.state.field.ball_position,
                                             player_id=player_id, rolls=[roll_scatter]))

                # On ground
                else:
                    self.game.report(Outcome(OutcomeType.BALL_ON_GROUND, pos=self.game.state.field.ball_position,
                                             team_home=self.home))

        return True