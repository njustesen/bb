from core import Procedure, KnockDown, Turnover, Push, GFI, Armor
from model import Skill, Outcome, OutcomeType, DiceRoll, BBDieResult, BBDie, D6, ActionType
from exception import IllegalActionExcpetion


class Foul(Procedure):

    def __init__(self, game, home, player_from, player_to, pos_to, gfi):
        super().__init__(game)
        self.home = home
        self.player_from = player_from
        self.player_to = player_to
        self.pos_from = self.game.state.field.get_player_position(player_from.player_id)
        self.pos_to = pos_to
        self.gfi = gfi
        self.waiting_gfi = False

    def step(self, action):

        # GfI
        if self.gfi:
            self.gfi = False
            GFI(self.game, self.home, self.player_from, self.pos_from, self.pos_to)
            return False

        # Assists
        assists_from = self.game.state.field.assists(self.home, self.player_from, self.player_to, ignore_guard=True)
        assists_to = self.game.state.field.assists(not self.home, self.player_to, self.player_from, ignore_guard=True)

        # Roll
        roll = DiceRoll([D6(), D6()])
        roll.modifiers = assists_from - assists_to
        result = self.roll.get_sum()

        # Effect
        Armor(self.game, self.home, self.player_to.player_id, modifiers=roll.modifiers, opp_player_id=self.player_from.player_id, foul=True)

        return True