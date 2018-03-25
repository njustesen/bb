from core import Procedure, CasualtyEffect, CasualtyType, Apothecary
from model import Outcome, OutcomeType, Rules, ActionType, DiceRoll, D6, D8, PlayerState


class Casualty(Procedure):

    miss_next_game = [CasualtyEffect.MNG, CasualtyEffect.AG, CasualtyEffect.AV, CasualtyEffect.MA, CasualtyEffect.ST, CasualtyEffect.NI]

    def __init__(self, game, home, player_id, opp_player_id=None):
        super().__init__(game)
        self.game = game
        self.home = home
        self.player_id = player_id
        self.opp_player_id = opp_player_id
        self.player = game.get_player(player_id)
        self.opp_player = game.get_player(opp_player_id)
        self.waiting_apothecary = False
        self.roll = None
        self.casualty = None
        self.effect = None

    def step(self, action):

        if self.roll is None:
            self.roll = DiceRoll([D6(), D8()])
            result = self.roll.get_sum()
            n = min(61, max(38, result))
            self.casualty = CasualtyType(n)
            self.effect = Rules.casualty_effect[self.casualty]

            self.game.report(Outcome(OutcomeType.CASUALTY, player_id=self.player_id, team_home=self.home, n=[self.casualty, self.effect], rolls=[self.roll]))

            if self.game.state.get_team_state(self.home).apothecary:
                self.waiting_apothecary = True
                return False

            return True

        elif self.waiting_apothecary:

            if action.action_type == ActionType.USE_APOTHECARY:
                Apothecary(self.game, self.home, self.player_id, roll=self.roll, outcome=OutcomeType.CASUALTY, casualty=self.casualty, effect=self.effect, opp_player_id=self.opp_player_id)
                return True

            # Apply casualty
            if self.effect == CasualtyEffect.NONE:
                self.game.state.get_team_state(self.home).player_states[self.player_id] = PlayerState.BH
            elif self.effect in Casualty.miss_next_game:
                self.game.state.get_team_state(self.home).player_states[self.player_id] = PlayerState.MNG
            elif self.effect == CasualtyEffect.DEAD:
                self.game.state.get_team_state(self.home).player_states[self.player_id] = PlayerState.DEAD

            self.game.state.get_team_state(self.home).injuries.put(self.player_id, self.effect)
            self.game.state.field.remove(self.player_id)
            self.game.state.get_dugout(self.home).casualties.append(self.player_id)

        return True