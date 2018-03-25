from core import Procedure, Bounce, ThrowIn, Catch
from model import Outcome, OutcomeType, ActionType, DiceRoll, D6, D8, PlayerState, Skill, WeatherType


class Scatter(Procedure):

    def __init__(self, game, home, kick=False, is_pass=False):
        super().__init__(game)
        self.home = home  # Having the turn
        self.kick = kick
        self.is_pass = is_pass

    def step(self, action):

        # Roll
        roll_scatter = DiceRoll([D8()])
        if self.kick:
            roll_distance = DiceRoll([D6()])

        # Scatter
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
        distance = 1 if not self.kick else roll_distance.get_sum()

        n = 3 if self.is_pass else 1

        for x in range(n):
            for i in range(distance):
                # Move ball on square
                self.game.state.field.ball_position[0] += x
                self.game.state.field.ball_position[1] += y

                # Check out of bounds
                if self.kick:
                    if self.game.state.field.is_ball_out() or \
                            self.game.arena.is_team_side(self.game.state.field.ball_position, not self.home):
                        # Touchback will be enforced in after kick-off table when ball lands
                        self.game.report(Outcome(OutcomeType.KICK_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                       team_home=self.home, rolls=[roll_scatter, roll_distance]))
                else:
                    # Throw in
                    if self.game.state.field.is_ball_out():
                        # Move ball back
                        self.game.state.field.ball_position[0] -= x
                        self.game.state.field.ball_position[1] -= y
                        ThrowIn(self.game, self.home, self.game.state.field.ball_position)
                        self.game.report(Outcome(OutcomeType.BALL_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                       team_home=self.home, rolls=[roll_scatter]))
                        return True

                    # Keep scattering passes until the last
                    if self.is_pass and x < n-1:
                        continue

                    # On player -> Catch
                    player_id = self.game.field.get_player_id_at(self.game.state.field.ball_position)
                    if player_id is not None:
                        Catch(self.game, self.home, player_id, self.game.state.field.ball_position)
                        self.game.report(Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.game.state.field.ball_position,
                                       player_id=player_id, rolls=[roll_scatter]))
                        return True

        if self.kick:
            # Wait for ball to land
            self.game.report(Outcome(OutcomeType.KICK_IN_BOUNDS, pos=self.game.state.field.ball_position, team_home=self.home))
        else:
            # Bounce ball
            Bounce(self.game, self.home)
            self.game.report(Outcome(OutcomeType.BALL_HIT_GROUND, pos=self.game.state.field.ball_position, team_home=self.home))

        return True
