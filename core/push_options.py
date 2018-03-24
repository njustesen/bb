from core import Procedure
from model import Outcome, OutcomeType, ActionType, DiceRoll, D3, D6, D8, PlayerState, Skill, WeatherType


class PushOptions(Procedure):

    def __init__(self, game, home, player_from, player_to):
        super().__init__(game)
        self.home = home  # With turn
        self.player_from = player_from
        self.player_to = player_to

    def push_squares(self):
        

    def step(self, action):

        # Find empty squares
        pos_from = self.game.state.field.get_player_position(self.player_from.player_id)
        pos_to = self.game.state.field.get_player_position(self.player_from.player_id)

        squares = push_squares(pos_from, pos_to)