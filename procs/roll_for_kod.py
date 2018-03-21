from procs.procedure import Procedure
from model.action import Action
from model.outcome import Outcome
from model.outcome_type import OutcomeType
from model.dice import *
from model.playerstate import PlayerState


class RollForKOd(Procedure):

    def __init__(self, game, home):
        self.game = game
        self.home = home
        self.idx = 0
        self.checked = []
        super().__init__()

    def step(self, action):
        if self.home:
            for id, state in self.game.state.home_player_states.items():
                if state == PlayerState.KOD and id not in self.checked:
                    roll = DiceRoll([D6()])
                if roll.get_sum() >= 4:
                    self.game.state.home_player_states[id] = PlayerState.READY
                    self.checked.append(id)
                    return Outcome(OutcomeType.PLAYER_READY, player_id=id, rolls=[roll]), False
                self.idx += 1
                return Outcome(OutcomeType.PLAYER_NOT_READY, player_id=id, rolls=[roll]), False
        return Outcome(OutcomeType.DONE), True
