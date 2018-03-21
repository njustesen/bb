from procs.procedure import Procedure
from procs.place_ball import PlaceBall
from procs.kickoff_table import KickOffTable
from model.outcome import Outcome, OutcomeType
from model.dice import DiceRoll, D6, D8


class Touchback(Procedure):

    def __init__(self, game, home):
        self.game = game
        self.home = home
        super().__init__()

    def step(self, action):
        assert action in [ActionType.PLACE_BALL] and action.pos_to is not None
        player_id = self.game.state.field.get_player_id_at(action.pos_to)
        if player_id is None or self.game.is_on_team(player_id, home=not self.home):
            return Outcome(OutcomeType.NOT_ALLOWED, pos=action.pos_to), False
        self.game.state.field.ball_position = action.pos_to
        return Outcome(OutcomeType.BALL_PLACED, pos=action.pos_to), True


class BounceKick(Procedure):

    def __init__(self, game, home):
        self.game = game
        self.home = home  # Kicking team
        super().__init__()

    def step(self, action):
        roll_scatter = DiceRoll([D8])

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
        if self.game.state.field.is_ball_out() or \
                self.game.arena.is_team_side(self.game.state.field.ball_position, not self.home):
            return Outcome(OutcomeType.TOUCHBACK, pos=self.game.state.field.ball_position,
                           team_home=self.home, rolls=[roll_scatter]), True

        return Outcome(OutcomeType.BALL_ON_GROUND, pos=self.game.state.field.ball_position, team_home=self.home), True


class LandKick(Procedure):

    def __init__(self, game, home):
        self.game = game
        self.home = home  # Kicking team
        self.procedures = []
        self.landed = False
        super().__init__()

    def step(self, action):
        if self.landed:
            outcome, terminal = self.procedures[0].step(action)
            if outcome.terminal:
                self.procedures.pop()
                if len(self.procedures) == 0:
                    return outcome, True
            return outcome, False
        else:
            if not self.game.arena.is_team_side(self.game.state.field.ball_position, not self.home):
                self.procedures.insert(0, Touchback(self.game, home=not self.home))
                return Outcome(OutcomeType.TOUCHBACK, team_home=not self.home), False
            else:
                player_id = self.game.state.field.get_player_id_at(self.game.state.field.ball_position)
                if player_id is None:
                    self.procedures.insert(0, BounceKick(self.game, home=self.home))
                    return Outcome(OutcomeType.BALL_HIT_GROUND, pos=self.game.state.field.ball_position, team_home=self.home), False
                else:
                    self.procedures.insert(0, Catch(self.game, player_id=player_id))
                    return Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.game.state.field.ball_position, team_home=not self.home), False


class ScatterKick(Procedure):

    def __init__(self, game, home):
        self.game = game
        self.home = home  # Kicking team
        super().__init__()

    def step(self, action):
        roll_scatter = DiceRoll([D8])
        roll_distance = DiceRoll([D6])

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

        distance = roll_distance.get_sum()
        if self.game.state.gentle_gust:
            distance += 1

        for i in range(distance):
            self.game.state.field.ball_position[0] += x
            self.game.state.field.ball_position[1] += y
            if self.game.state.field.is_ball_out() or \
                    self.game.arena.is_team_side(self.game.state.field.ball_position, not self.home):
                return Outcome(OutcomeType.KICK_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                               team_home=self.home, rolls=[roll_scatter, roll_distance]), True

        return Outcome(OutcomeType.KICK_IN_BOUNDS, pos=self.game.state.field.ball_position, team_home=self.home), True


class KickOff(Procedure):

    def __init__(self, game, home):
        self.game = game
        self.kicking_home = home
        self.game.state.gentle_gust = False
        self.procedures = []
        self.procedures.append(PlaceBall(game, home=self.kicking_home))
        self.procedures.append(ScatterKick(game, home=self.kicking_home))
        self.procedures.append(KickOffTable(game, home=self.kicking_home))
        self.procedures.append(LandKick(game, home=self.kicking_home))
        super().__init__()

    def step(self, action):
        outcome, terminal = self.procedures[0].step(action)
        if outcome.terminal:
            self.procedures.pop()
            if len(self.procedures) == 0:
                return outcome, True
        return outcome, False
