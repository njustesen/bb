from procs.procedure import Procedure
from model.action import Action, ActionType
from model.outcome import Outcome, OutcomeType
import numpy as np
from model.dice import *


class Catch(Procedure):

    #          0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    success = [6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1]

    def __init__(self, game, player_id, pos, accurate=False):
        self.game = game
        self.player_id = player_id
        self.pos = pos
        self.accurate = accurate
        super().__init__()

    def step(self, action):
        modifiers = 1 if self.accurate else 0
        tackle_zones = self.game.state.field.in_tackle_zones(self.player_id)
        modifiers -= tackle_zones
        player = self.game.get_player(self.player_id)
        team = self.game.get_team_by_player_id(self.player_id)
        mod_ag = max(0, min(player.get_ag() + modifiers, 10))
        target = Catch.success[mod_ag]
        roll = DiceRoll([D6], target=target)
        if roll.get_sum() >= target:
            return Outcome(OutcomeType.CATCH, player_id=self.player_id)
        else:
            return Outcome(OutcomeType.DROP, player_id=self.player_id)