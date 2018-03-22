from procs.procedure import Procedure
from model.action import Action
from model.outcome import Outcome
from model.outcome_type import OutcomeType
from model.dice import *
from model.playerstate import PlayerState


class PreHalf(Procedure):

    def __init__(self, game, home):
        self.game = game
        self.home = home
        self.checked = []
        super().__init__()

    def step(self, action):
        for id, state in self.game.state.get_team_state(self.home).player_states.items():
            if state == PlayerState.KOD and id not in self.checked:
                roll = DiceRoll([D6()])
                if roll.get_sum() >= 4:
                    self.game.state.get_team_state(self.home).player_states[id] = PlayerState.READY
                    self.checked.append(id)
                    return Outcome(OutcomeType.PLAYER_READY, player_id=id, rolls=[roll]), False
                return Outcome(OutcomeType.PLAYER_NOT_READY, player_id=id, rolls=[roll]), False
        self.game.state.reset_kickoff(self.home).reset()
        return Outcome(OutcomeType.DONE), True
