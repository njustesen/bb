from core import Procedure, KnockOut, Casualty, Turnover, Ejection
from model import Outcome, OutcomeType, DiceRoll, D6, PlayerState, Skill


class Injury(Procedure):

    def __init__(self, game, home, player_id, opp_player_id=None, foul=False, mighty_blow_used=False, dirty_player_used=False,
                 ejected=False):
        super().__init__(game)
        self.game = game
        self.home = home
        self.player_id = player_id
        self.opp_player_id = opp_player_id
        self.injury_rolled = False
        self.foul = foul
        self.mighty_blow_used = mighty_blow_used
        self.dirty_player_used = dirty_player_used
        self.ejected = ejected
        self.player = game.get_player(player_id)
        self.opp_player = game.get_player(opp_player_id)
        self.apothecary_used = False

    def step(self, action):

        # TODO: Necromancer

        # Roll
        roll = DiceRoll(D6(), D6())
        result = roll.get_sum()
        self.injury_rolled = True

        # Skill modifiers
        thick_skull = -1 if self.player.has_skill(Skill.THICK_SKULL) else 0
        stunty = 1 if self.player.has_skill(Skill.STUNTY) else 0
        mighty_blow = 1 if self.opp_player.has_skill(Skill.MIGHTY_BLOW) and not self.mighty_blow_used and not self.foul else 0
        dirty_player = 1 if self.opp_player.has_skill(Skill.DIRTY_PLAYER) and not self.dirty_player_used and self.foul else 0

        # STUNNED
        if result + thick_skull + stunty + mighty_blow + dirty_player <= 7:
            roll.modifiers = thick_skull + stunty + mighty_blow + dirty_player
            if self.game.get_player(self.player_id).has_skill(Skill.BALL_AND_CHAIN):
                self.game.state.set_player_state(self.player_id, self.home, PlayerState.KOD)
                self.game.state.field.remove(self.player_id)
                self.game.state.get_dugout(self.home).kod.append(self.player_id)
                self.game.report(Outcome(OutcomeType.KNOCKED_OUT, player_id=self.player_id, rolls=[roll]))
            else:
                self.game.state.get_home_state(self.home).player_states[self.player_id] = PlayerState.STUNNED
                self.game.report(Outcome(OutcomeType.STUNNED, player_id=self.player_id, rolls=[roll]))

        # CASUALTY
        elif result + stunty + mighty_blow + dirty_player >= 10:
            roll.modifiers = stunty + mighty_blow + dirty_player
            self.game.state.badly_hurt(self.player_id)
            self.game.report(Outcome(OutcomeType.CASUALTY, player_id=self.player_id, rolls=[roll]))
            Casualty(self.game, self.home, self.player_id)

        # KOD
        else:
            roll.modifiers = thick_skull + stunty + mighty_blow + dirty_player
            self.game.state.knock_out(self.player_id)
            self.game.report(Outcome(OutcomeType.KNOCKED_OUT, player_id=self.player_id, rolls=[roll]))
            KnockOut(self.game, self.home, self.player_id)

        # Referee
        if self.foul and not self.ejected:
            if roll.same():
                if not self.opp_player.has_skill(Skill.SNEAKY_GIT):
                    self.game.report(Outcome(OutcomeType.PLAYER_EJECTED, player_id=self.opp_player_id))
                    Turnover(self.game, self.home)
                    Ejection(self.game, self.home, self.player_id)

        return True
