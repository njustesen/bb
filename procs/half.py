from procs.procedure import Procedure
from model.outcome import OutcomeType
from procs.roll_for_kod import RollForKOd
from procs.setup import Setup
from procs.kickoff import KickOff
from procs.turn import Turn


class Half(Procedure):

    def __init__(self, game):
        self.game = game
        self.procedures = []
        if game.state.half > 1:
            self.procedures.append(RollForKOd(game, True))
            self.procedures.append(RollForKOd(game, False))
        kicking_home = game.state.kicking_team if game.state.half == 1 else not game.state.kicking_team
        self.procedures.append(Setup(game, home=kicking_home))
        self.procedures.append(Setup(game, home=not kicking_home))
        self.procedures.append(KickOff(game, kicking_home))
        for i in range(8):
            self.procedures.append(Turn(game, home=True))
            self.procedures.append(Turn(game, home=False))
        super().__init__()

    def step(self, action):
        outcome, terminal = self.procedures[0].step(action)
        if outcome.terminal:
            self.procedures.pop()
            if len(self.procedures) == 0:
                return outcome, True
            if outcome.outcome_type == OutcomeType.TOUCHDOWN:
                kicking_home = outcome.team_home
                if self.game.state.get_team_state(not kicking_home).turn < 8:
                    self.procedures.append(RollForKOd(self.game, True))
                    self.procedures.append(RollForKOd(self.game, False))
                    self.procedures.append(Setup(self.game, home=kicking_home))
                    self.procedures.append(Setup(self.game, home=not kicking_home))
                    self.procedures.append(KickOff(self.game, home=kicking_home))

        return outcome, False
