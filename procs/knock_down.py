from procs.procedure import Procedure
from model.outcome import Outcome, OutcomeType
from model.player import *
from model.dice import *


class Injury(Procedure):

    def __init__(self, game, home, player_id, opp_player_id=None, mighty_blow_used=False):
        self.game = game
        self.home = home
        self.player_id = player_id
        self.opp_player_id = opp_player_id
        self.injury_rolled = False
        self.mighty_blow_used = mighty_blow_used
        self.player = game.get_player(player_id)
        self.opp_player = game.get_player(opp_player_id)
        super().__init__()

    def step(self, action):

        # Roll
        roll = DiceRoll(D6(), D6())
        result = roll.get_sum()
        self.injury_rolled = True

        # Skill modifiers
        thick_skull = -1 if self.player.has_skill(Skill.THICK_SKULL) else 0
        stunty = 1 if self.player.has_skill(Skill.STUNTY) else 0
        mighty_blow = 1 if self.opp_player.has_skill(Skill.MIGHTY_BLOW) and not self.mighty_blow_used else 0

        # Result
        if result + thick_skull + stunty + mighty_blow <= 7:
            roll.modifiers = thick_skull + stunty + mighty_blow
            self.game.state.get_team(self.home).player_states[self.player_id] = PlayerState.STUNNED
            return Outcome(OutcomeType.STUNNED, player_id=self.player_id, rolls=[roll]), True
        elif result + stunty + mighty_blow >= 10:
            roll.modifiers = stunty + mighty_blow
            self.game.state.badly_hurt(self.player_id)
            # TODO: Insert casualty roll procedure
            return Outcome(OutcomeType.BADLY_HURT, player_id=self.player_id, rolls=[roll]), True
        else:
            roll.modifiers = thick_skull + stunty + mighty_blow
            self.game.state.knock_out(self.player_id)
            return Outcome(OutcomeType.KNOCKED_OUT, player_id=self.player_id, rolls=[roll]), True


class Armor(Procedure):

    def __init__(self, game, home, player_id, modifiers=0, opp_player_id=None):
        self.game = game
        self.home = home
        self.player_id = player_id
        self.modifiers = modifiers
        self.opp_player_id = opp_player_id
        self.skip_armor = False
        self.procedures = []
        self.armor_rolled = False
        self.player = game.get_player(player_id)
        self.opp_player = None
        if self.opp_player_id is not None:
            self.opp_player = game.get_player(opp_player_id)
        super().__init__()

    def step(self, action):

        # Only roll armor once
        if not self.armor_rolled:

            # ROll
            roll = DiceRoll(D6(), D6())
            roll.modifiers = self.modifiers
            result = roll.get_sum()
            self.armor_rolled = True

            # Result
            if result >= 8 and self.opp_player is not None and self.opp_player.has_skill(Skill.CLAWS):
                self.procedures.insert(0, Injury(self.game, self.home, self.player_id, self.opp_player_id))
                return Outcome(OutcomeType.ARMOR_BROKEN, player_id=self.player_id, rolls=[roll]), False
            if result > self.player.get_av():
                self.procedures.insert(0, Injury(self.game, self.home, self.player_id, self.opp_player_id))
                return Outcome(OutcomeType.ARMOR_BROKEN, player_id=self.player_id, rolls=[roll]), False
            if self.opp_player is not None and self.player.has_skill(Skill.MIGHTY_BLOW) and result + 1 > self.player.get_av():
                roll.modifiers += 1
                self.procedures.insert(0, Injury(self.game, self.home, self.player_id, self.opp_player_id, mighty_blow_used=True))
                return Outcome(OutcomeType.ARMOR_BROKEN, player_id=self.player_id, rolls=[roll]), False

            return Outcome(OutcomeType.ARMOR_NOT_BROKEN, player_id=self.player_id, rolls=[roll]), True

        # Continue procedures until terminal
        outcome, terminal = self.procedures[0].step(action)
        if outcome.terminal:
            self.procedures.pop()
            if len(self.procedures) == 0:
                return outcome, True
        return outcome, False


class KnockDown(Procedure):

    def __init__(self, game, home, player_id, skip_armor_roll=True, no_armor_roll=False, modifiers=0, opp_player_id=None, in_crowd=False):
        self.game = game
        self.home = home
        self.player_id = player_id
        self.skip_armor_roll = skip_armor_roll
        self.no_armor_roll = no_armor_roll
        self.modifiers = modifiers
        self.opp_player_id = opp_player_id
        self.procedures = []
        self.knocked_down = False
        self.proc_added = False
        self.in_crowd = in_crowd
        super().__init__()

    def step(self, action):

        # Knock down player
        if not self.knocked_down:
            self.game.state.get_team(self.home).player_states[self.player_id] = PlayerState.DOWN
            self.knocked_down = True
            # Terminal if no armor roll should be made
            return Outcome(OutcomeType.KNOCKED_DOWN, player_id=self.player_id, opp_player_id=self.opp_player_id), self.no_armor_roll

        # Only add proc once
        if not self.proc_added:
            self.proc_added = True
            # If armor roll should be made
            if not self.skip_armor_roll:
                self.procedures.insert(0, Armor(self.game, self.home, self.player_id, modifiers=self.modifiers,
                                                opp_player_id=self.opp_player_id if not self.in_crowd else None))
            else:
                self.procedures.insert(0, Injury(self.game, self.home, self.player_id,
                                                 opp_player_id=self.opp_player_id if not self.in_crowd else None))

        outcome, terminal = self.procedures[0].step(action)
        if outcome.terminal:
            self.procedures.pop()
            if len(self.procedures) == 0:
                return outcome, True
        return outcome, False