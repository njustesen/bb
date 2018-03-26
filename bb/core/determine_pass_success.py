from core import Procedure, Turnover
#from model import


class DeterminePassSuccess(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.game = game
        self.home = home

    def step(self, action):

        ball_at = self.game.state.field.ball_position
        player_at = self.game.state.field.get_player_id_at(ball_at)
        if player_at is None or self.game.get_home_by_player_id(player_at) != self.home:
            Turnover(self.game, self.home)

        return True
