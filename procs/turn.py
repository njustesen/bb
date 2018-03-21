from procs.procedure import Procedure


class Turn(Procedure):

    def __init__(self, game, home, blitz=False, quick_snap=False):
        self.game = game
        self.procedures = []
        self.home = home
        self.blitz = blitz
        self.quick_snap = quick_snap
        super().__init__()

    def step(self, action):
        outcome, terminal = self.procedures[0].step(action)
        if outcome.terminal:
            self.procedures.pop()
            if len(self.procedures) == 0:
                return outcome, True
        return outcome, False
