from procs.procedure import Procedure
from model.action import Action, ActionType
from model.outcome import Outcome, OutcomeType
import numpy as np
from model.dice import *


class KnockDown(Procedure):

    def __init__(self, game, home, player_id, pos, armor=True):
        self.game = game
        self.home = home
        self.player_id = player_id
        self.pos = pos
        self.armor = armor
        super().__init__()

    def step(self, action):
        # TODO