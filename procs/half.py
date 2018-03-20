from procs.procedure import Procedure
from model.outcome_type import OutcomeType
from procs.roll_for_kod import RollForKOd


class Half(Procedure):

    def __init__(self, game):
        self.game = game
        self.procedures = []
        if game.state.half > 1:
            self.procedures.append(RollForKOd(game, True))
            self.procedures.append(RollForKOd(game, False))
        kicking_home = game.state.kicking_team if game.state.half == 1 else game.state.kicking_team
        self.procedures.append(KickingSetup(game, home=kicking_home))
        self.procedures.append(ReceivingSetup(game, home=not kicking_home))
        self.procedures.append(Kickoff(game, home=kicking_home))
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
                self.procedures.append(RollForKOd(self.game, True))
                self.procedures.append(RollForKOd(self.game, False))
                kicking_home = not outcome.team_home
                self.procedures.append(KickingSetup(self.game, home=kicking_home))
                self.procedures.append(ReceivingSetup(self.game, home=not kicking_home))
                self.procedures.append(Kickoff(self.game, home=kicking_home))

        return outcome, False
