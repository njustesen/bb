from core import Procedure
from model import Outcome, OutcomeType, PlayerState, DiceRoll, D6


class PreHalf(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.home = home
        self.checked = []

    def step(self, action):
        for player_id, state in self.game.state.get_team_state(self.home).player_states.items():
            if state == PlayerState.KOD and player_id not in self.checked:
                roll = DiceRoll([D6()])
                if roll.get_sum() >= 4:
                    self.game.state.get_team_state(self.home).player_states[player_id] = PlayerState.READY
                    self.checked.append(player_id)
                    self.game.report(Outcome(OutcomeType.PLAYER_READY, player_id=player_id, rolls=[roll]))
                    return False
                self.game.report(Outcome(OutcomeType.PLAYER_NOT_READY, player_id=player_id, rolls=[roll]))
                return False
        self.game.state.reset_kickoff(self.home).reset()
        return True
