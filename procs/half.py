from procs.procedure import Procedure
from model.outcome import OutcomeType
from procs.roll_for_kod import PreHalf
from procs.setup import Setup
from procs.kickoff import KickOff
from procs.turn import Turn


class Half(Procedure):

    def __init__(self, game):
        self.game = game
        self.procedures = []
        if game.state.half > 1:
            self.procedures.append(PreHalf(game, True))
            self.procedures.append(PreHalf(game, False))
        self.kicking_home = game.state.kicking_team if game.state.half == 1 else not game.state.kicking_team
        self.procedures.append(Setup(game, home=self.kicking_home))
        self.procedures.append(Setup(game, home=not self.kicking_home))
        self.procedures.append(KickOff(game, self.kicking_home))
        for i in range(8):
            self.procedures.append(Turn(game, home=not self.kicking_home))
            self.procedures.append(Turn(game, home=self.kicking_home))
        super().__init__()

    def step(self, action):
        outcome, terminal = self.procedures[0].step(action)
        if outcome.terminal:
            self.procedures.pop()
            if len(self.procedures) == 0:
                return outcome, True

            if outcome.outcome_type == OutcomeType.TOUCHDOWN:
                scoring_home = outcome.team_home
                if self.game.state.get_team_state(not scoring_home).turn < 8:
                    self.procedures.append(PreHalf(self.game, True))
                    self.procedures.append(PreHalf(self.game, False))
                    self.procedures.append(Setup(self.game, home=scoring_home))
                    self.procedures.append(Setup(self.game, home=not scoring_home))
                    self.procedures.append(KickOff(self.game, home=scoring_home))

            elif outcome.outcome_type == OutcomeType.RIOT:
                if n == 1:
                    self.procedures.append(Turn(self.game, home=not self.kicking_home))
                    self.procedures.append(Turn(self.game, home=self.kicking_home))
                else:
                    self.procedures = self.procedures[:-2]

        return outcome, False
