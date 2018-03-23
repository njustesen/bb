from procs.procedure import Procedure
from model.outcome import *
from procs.pre_half import PreHalf
from procs.setup import Setup
from procs.kickoff import KickOff
from procs.turn import Turn


class Half(Procedure):

    def __init__(self, game, half):
        super().__init__(game)
        self.half = half

        # Determine kicking team
        self.kicking_home = self.game.state.kicking_team if self.game.state.half == 1 else not self.game.state.kicking_team

        # Add turns
        for i in range(8):
            Turn(self.game, home=self.kicking_home)
            Turn(self.game, home=not self.kicking_home)

        # Setup and kickoff
        KickOff(self.game, self.kicking_home)
        Setup(self.game, home=not self.kicking_home)
        Setup(self.game, home=self.kicking_home)
        ClearBoard(self.game)

        # If second half
        if self.half > 1:
            PreHalf(self.game, False)
            PreHalf(self.game, True)

    def step(self, action):
        self.game.report(Outcome(OutcomeType.END_OF_HALF))
        return True
