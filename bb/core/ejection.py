from core import Procedure
from model import Outcome, OutcomeType, PlayerState


class Ejection(Procedure):

    def __init__(self, game, home, player_id):
        super().__init__(game)
        self.home = home  # With turn
        self.player_id = player_id

    def step(self, action):

        self.game.state.field.remove(self.player_id)
        self.game.state.get_dugout(self.home).dungeon.append(self.player_id)
        self.game.state.set_player_state(self.player_id, self.home, PlayerState.EJECTED)

        return True