from procs.procedure import Procedure
from model.outcome import Outcome, OutcomeType
from procs.roll_for_kod import PreHalf
from model.action import *
from model.arena import Tile
from model.exceptions import *


class Setup(Procedure):

    def __init__(self, game, home, reorganize=False):
        self.game = game
        self.home = home
        self.reorganize = reorganize
        super().__init__()

    def step(self, action):

        if action.action_type == ActionType.PLACE_PLAYER:
            if self.game.arena.is_team_side(action.pos_to, self.home):
                if action.pos_from is None:  # From reserves
                    if self.reorganize:
                        return Outcome(OutcomeType.NOT_ALLOWED, team_home=self.home), False
                    self.game.state.get_dugout(self.home).remove(action.player_from_id)
                elif action.pos_to is None:  # To reserves
                    if self.reorganize:
                        return Outcome(OutcomeType.NOT_ALLOWED, team_home=self.home), False
                    self.game.state.field.remove(action.player_from_id)
                    self.game.state.get_dugout(self.home).add_to_reserves(action.player_from_id)
                else:
                    self.game.state.field.swap(action.pos_from, action.pos_to)
                return Outcome(OutcomeType.PLAYER_PLACED, pos=action.pos_to, player_id=action.player_from_id), False
            raise IllegalActionExcpetion("Not allowed to place players at that location")
        elif action.action_type == ActionType.END_SETUP:
            if not self.game.state.field.is_setup_legal(self.home):
                return Outcome(OutcomeType.ILLEGAL_SETUP_NUM, team_home=self.home), False
            elif not self.game.state.field.is_setup_legal_scrimmage(self.home):
                return Outcome(OutcomeType.ILLEGAL_SETUP_SCRIMMAGE, team_home=self.home), False
            elif not self.game.state.field.is_setup_legal_wings(self.home):
                return Outcome(OutcomeType.ILLEGAL_SETUP_WINGS, team_home=self.home), False
            return Outcome(OutcomeType.SETUP_DONE, team_home=self.home), True

