from procs.procedure import Procedure
from procs.place_ball import PlaceBall
from procs.kickoff_table import KickOffTable
from procs.catch import *
from model.outcome import Outcome, OutcomeType
from model.dice import DiceRoll, D6, D8
from model.exceptions import *


class Touchback(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.home = home

    def step(self, action):
        player_id = self.game.state.field.get_player_id_at(action.pos_to)
        if player_id is None or self.game.is_on_team(player_id, home=not self.home):
            raise IllegalActionExcpetion("You must pick a player on your own team")
        self.game.state.field.move_ball(action.pos_to)
        self.game.report(Outcome(OutcomeType.BALL_PLACED, pos=action.pos_to))
        return True


class LandKick(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.home = home  # Kicking team
        self.landed = False

    def step(self, action):
        if not self.game.arena.is_team_side(self.game.state.field.ball_position, not self.home):
            Touchback(self.game, home=not self.home)
            self.game.report(Outcome(OutcomeType.TOUCHBACK, team_home=not self.home))
            return True
        else:
            player_id = self.game.state.field.get_player_id_at(self.game.state.field.ball_position)
            if player_id is None:
                Bounce(self.game, home=self.home, kick=True)
                self.game.report(Outcome(OutcomeType.BALL_HIT_GROUND, pos=self.game.state.field.ball_position, team_home=self.home))
                return True
            else:
                Catch(self.game, self.home, player_id=player_id, pos=self.game.state.field.ball_position)
                self.game.report(Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.game.state.field.ball_position, team_home=not self.home))
                return True


class KickOff(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.kicking_home = home
        self.game.state.gentle_gust = False
        self.game.state.reset_kickoff()
        LandKick(game, home=self.kicking_home)
        KickOffTable(game, home=self.kicking_home)
        Scatter(game, home=self.kicking_home, kick=True)
        PlaceBall(game, home=self.kicking_home)

    def step(self, action):
        return True
