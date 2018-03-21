from procs.procedure import Procedure
from model.action import Action, ActionType
from model.outcome import Outcome, OutcomeType
import numpy as np
from model.dice import *


class InjuryRoll(Procedure):

    def __init__(self, game, home, player_id, pos):
        self.game = game
        self.home = home
        self.player_id = player_id
        self.pos = pos
        super().__init__()

    def step(self, action):
        # TODO