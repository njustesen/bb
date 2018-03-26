from core import Procedure, Apothecary
from model import OutcomeType, ActionType, PlayerState


class KnockOut(Procedure):

    def __init__(self, game, home, player_id, opp_player_id=None):
        super().__init__(game)
        self.game = game
        self.home = home
        self.player_id = player_id
        self.opp_player_id = opp_player_id
        self.player = game.get_player(player_id)
        self.opp_player = game.get_player(opp_player_id)
        self.waiting_apothecary = False
        self.roll = None

    def step(self, action):

        if action.action_type == ActionType.USE_APOTHECARY:
            Apothecary(self.game, self.home, self.player_id, roll=self.roll, outcome=OutcomeType.KNOCKED_OUT, opp_player_id=self.opp_player_id)
            return True

        self.game.state.get_team_state(self.home).player_states[self.player_id] = PlayerState.KOD
        self.game.state.field.remove(self.player_id)
        self.game.state.get_dugout(self.home).kod.append(self.player_id)

        return True