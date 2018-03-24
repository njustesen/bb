from procs.procedure import Procedure
from procs.catch import *
from procs.turn import *
from model.outcome import Outcome, OutcomeType
from model.player import *
from model.dice import *
from enum import Enum


class Apothecary(Procedure):

    def __init__(self, game, home, player_id, roll, outcome, opp_player_id, casualty=None, effect=None):
        super().__init__(game)
        self.game = game
        self.home = home
        self.player_id = player_id
        self.opp_player_id = opp_player_id
        self.player = game.get_player(player_id)
        self.opp_player = game.get_player(opp_player_id)
        self.waiting_apothecary = False
        self.roll_first = roll
        self.roll_second = roll
        self.outcome = outcome
        self.casualty_first = casualty
        self.effect_first = effect
        self.casualty_second = None
        self.effect_second = None

    def step(self, action):

        if self.outcome == OutcomeType.KNOCKED_OUT:

            if action.action_type == ActionType.USE_APOTHECARY:

                # Player is moved to reserves
                self.game.state.field.remove(self.player_id)
                self.game.state.get_dugout(self.home).reserves.append(self.player_id)
                self.game.report(Outcome(OutcomeType.APOTHECARY_USED_KO, player_id=self.player_id, team_home=self.home))

            else:

                # Player is KO
                self.game.state.field.remove(self.player_id)
                self.game.state.get_dugout(self.home).kod.append(self.player_id)
                self.game.state.get_team_state(self.home).player_states[self.player_id] = PlayerState.KOD
                self.game.report(Outcome(OutcomeType.APOTHECARY_USED_KO, player_id=self.player_id, team_home=self.home))

            return True

        elif self.outcome == OutcomeType.CASUALTY:

            if action.action_type == ActionType.USE_APOTHECARY:

                self.roll_second = DiceRoll([D6(), D8()])
                result = self.roll_second.get_sum()
                n = max(38, result)
                n = min(61, result)
                self.casualty_second = CasualtyType(n)
                self.effect_second = Rules.casualty_effect[self.casualty_second]

                self.game.state.get_team_state(self.home).apothecary = False

                self.game.report(Outcome(OutcomeType.CASUALTY_APOTHECARY, player_id=self.player_id, team_home=self.home, n=[self.casualty_first, self.effect_first, self.casualty_second, self.effect_second], rolls=[self.roll_first, self.roll_second]))

                self.waiting_apothecary = True

                return False

            if action.action_type == ActionType.SELECT_ROLL:

                effect = self.effect_first if action.idx == 0 else self.effect_second
                casualty = self.casualty_first if action.idx == 0 else self.casualty_second
                roll = self.roll_first if action.idx == 0 else self.roll_second

                # Apply casualty
                if effect == CasualtyEffect.NONE:
                    self.game.state.get_team_state(self.home).player_states[self.player_id] = PlayerState.BH
                elif effect in Casualty.miss_next_game:
                    self.game.state.get_team_state(self.home).player_states[self.player_id] = PlayerState.MNG
                elif effect == CasualtyEffect.DEAD:
                    self.game.state.get_team_state(self.home).player_states[self.player_id] = PlayerState.DEAD

                self.game.state.field.remove(self.player_id)

                if effect != CasualtyEffect.NONE:
                    self.game.state.get_team_state(self.home).injuries.put(self.player_id, effect)
                    self.game.state.get_dugout(self.home).casualties.append(self.player_id)
                else:
                    # Apothecary puts badly hurt players in the reserves
                    self.game.state.get_dugout(self.home).reserves.append(self.player_id)

                self.game.report(Outcome(OutcomeType.CASUALTY, player_id=self.player_id, team_home=self.home, n=[casualty, effect], rolls=[roll]))

        return True


class CasualtyEffect(Enum):
    NONE = 1
    MNG = 2
    NI = 3
    MA = 4
    AV = 5
    AG = 6
    ST = 7
    DEAD = 8


class CasualtyType(Enum):
    '''
    D68 Result Effect
    11-38 Badly Hurt No long term effect
    41 Broken Ribs Miss next game
    42 Groin Strain Miss next game
    43 Gouged Eye Miss next game
    44 Broken Jaw Miss next game
    45 Fractured Arm Miss next game
    46 Fractured Leg Miss next game
    47 Smashed Hand Miss next game
    48 Pinched Nerve Miss next game
    51 Damaged Back Niggling Injury
    52 Smashed Knee Niggling Injury
    53 Smashed Hip -1 MA
    54 Smashed Ankle -1 MA
    55 Serious Concussion -1 AV
    56 Fractured Skull -1 AV
    57 Broken Neck -1 AG
    58 Smashed Collar Bone -1 ST
    61-68 DEAD Dead!
    '''
    BADLY_HURT = 38
    BROKEN_RIBS = 41
    GROIN_STRAIN = 42
    GOUGED_EYE = 43
    BROKEN_JAW = 44
    FRACTURED_ARM = 45
    FRACTURED_LEG = 46
    SMASHED_HAND = 47
    PINCHED_NERVE = 48
    DAMAGED_BACK = 51
    SMASHED_KNEE = 52
    SMASHED_HIP = 53
    SMASHED_ANKLE = 54
    SERIOUS_CONCUSSION = 55
    FRACTURED_SKULL = 56
    BROKEN_NECK = 57
    SMASHED_COLLAR_BONE = 58
    DEAD = 61


class KnockedOut(Procedure):

    def __init__(self, game, home, player_id, opp_player_id=None, mighty_blow_used=False):
        super().__init__(game)
        self.game = game
        self.home = home
        self.player_id = player_id
        self.opp_player_id = opp_player_id
        self.player = game.get_player(player_id)
        self.opp_player = game.get_player(opp_player_id)
        self.waiting_apothecary = False
        self.roll = None

    def step(self, action):

        if action.action_type == ActionType.USE_APOTHECARY:
            Apothecary(self.game, self.home, self.player_id, roll=self.roll, outcome=OutcomeType.KNOCKED_OUT, opp_player_id=self.opp_player_id)
            return True

        self.game.state.get_team_state(self.home).player_states[self.player_id] = PlayerState.KOD
        self.game.state.field.remove(self.player_id)
        self.game.state.get_dugout(self.home).kod.append(self.player_id)

        return True


class Casualty(Procedure):

    miss_next_game = [CasualtyEffect.MNG, CasualtyEffect.AG, CasualtyEffect.AV, CasualtyEffect.MA, CasualtyEffect.ST, CasualtyEffect.NI]

    def __init__(self, game, home, player_id, opp_player_id=None, mighty_blow_used=False):
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
            n = max(38, result)
            n = min(61, result)
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


class Injury(Procedure):

    def __init__(self, game, home, player_id, opp_player_id=None, mighty_blow_used=False):
        super().__init__(game)
        self.game = game
        self.home = home
        self.player_id = player_id
        self.opp_player_id = opp_player_id
        self.injury_rolled = False
        self.mighty_blow_used = mighty_blow_used
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
        mighty_blow = 1 if self.opp_player.has_skill(Skill.MIGHTY_BLOW) and not self.mighty_blow_used else 0

        # Result
        if result + thick_skull + stunty + mighty_blow <= 7:
            roll.modifiers = thick_skull + stunty + mighty_blow
            self.game.state.get_team(self.home).player_states[self.player_id] = PlayerState.STUNNED
            self.game.report(Outcome(OutcomeType.STUNNED, player_id=self.player_id, rolls=[roll]))
        elif result + stunty + mighty_blow >= 10:
            roll.modifiers = stunty + mighty_blow
            self.game.state.badly_hurt(self.player_id)
            self.game.report(Outcome(OutcomeType.CASUALTY, player_id=self.player_id, rolls=[roll]))
            Casualty(self.game, self.home, self.player_id)
        else:
            roll.modifiers = thick_skull + stunty + mighty_blow
            self.game.state.knock_out(self.player_id)
            self.game.report(Outcome(OutcomeType.KNOCKED_OUT, player_id=self.player_id, rolls=[roll]))
            KnockedOut(self.game, self.home, self.player_id)

        return True


class Armor(Procedure):

    def __init__(self, game, home, player_id, modifiers=0, opp_player_id=None):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.modifiers = modifiers
        self.opp_player_id = opp_player_id
        self.skip_armor = False
        self.armor_rolled = False
        self.player = game.get_player(player_id)
        self.opp_player = None
        if self.opp_player_id is not None:
            self.opp_player = game.get_player(opp_player_id)

    def step(self, action):

        # ROll
        roll = DiceRoll(D6(), D6())
        roll.modifiers = self.modifiers
        result = roll.get_sum()
        self.armor_rolled = True

        # Armor broken - Claws
        if result >= 8 and self.opp_player is not None and self.opp_player.has_skill(Skill.CLAWS):
            Injury(self.game, self.home, self.player_id, self.opp_player_id)
            self.game.report(Outcome(OutcomeType.ARMOR_BROKEN, player_id=self.player_id, rolls=[roll]))

        # Armor broken
        if result > self.player.get_av():
            Injury(self.game, self.home, self.player_id, self.opp_player_id)
            self.game.report(Outcome(OutcomeType.ARMOR_BROKEN, player_id=self.player_id, rolls=[roll]))

        # Armor broken - Might Blow
        if self.opp_player is not None and self.player.has_skill(Skill.MIGHTY_BLOW) and result + 1 > self.player.get_av():
            roll.modifiers += 1
            Injury(self.game, self.home, self.player_id, self.opp_player_id, mighty_blow_used=True)
            self.game.report(Outcome(OutcomeType.ARMOR_BROKEN, player_id=self.player_id, rolls=[roll]))

        self.game.report(Outcome(OutcomeType.ARMOR_NOT_BROKEN, player_id=self.player_id, rolls=[roll]))

        return True


class KnockDown(Procedure):

    def __init__(self, game, home, player_id, armor_roll=True, injury_roll=True, modifiers=0, opp_player_id=None, in_crowd=False, both_down=False, modifiers_opp=0,):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.armor_roll = armor_roll
        self.injury_roll = injury_roll
        self.modifiers = modifiers
        self.modifiers_opp = modifiers_opp
        self.opp_player_id = opp_player_id
        self.in_crowd = in_crowd
        self.both_down = both_down

    def step(self, action):

        # Knock down player
        self.game.state.get_team(self.home).player_states[self.player_id] = PlayerState.DOWN
        self.game.report(OutcomeType.KNOCKED_DOWN, player_id=self.player_id, opp_player_id=self.opp_player_id)
        if self.both_down:
            self.game.state.get_team(not self.home).player_states[self.opp_player_id] = PlayerState.DOWN
            self.game.report(OutcomeType.KNOCKED_DOWN, player_id=self.opp_player_id, opp_player_id=self.player_id)

        # If armor roll should be made. Injury is also nested in armor.
        if self.injury_roll:
            Injury(self.game, self.home, self.player_id, opp_player_id=self.opp_player_id if not self.in_crowd else None)
        if self.armor_roll:
            Armor(self.game, not self.home, self.player_id, modifiers=self.modifiers, opp_player_id=self.player_id)

        if self.both_down:
            if self.injury_roll:
                Injury(self.game, self.home, self.opp_player_id, opp_player_id=self.player_id if not self.in_crowd else None)
            if self.armor_roll:
                Armor(self.game, not self.home, self.opp_player_id, modifiers=self.modifiers, opp_player_id=self.player_id)

        # Check fumble
        pos = self.game.state.field.get_player_position(self.player_id)
        if self.game.state.ball_at(pos):
            Turnover(self.game, self.home)
            Bounce(self.game, self.home)
            self.game.report(Outcome(OutcomeType.FUMBLE, player_id=self.player_id, opp_player_id=self.opp_player_id))

        if self.both_down:
            pos = self.game.state.field.get_player_position(self.opp_player_id)
            if self.game.state.ball_at(pos):
                Bounce(self.game, not self.home)
                self.game.report(Outcome(OutcomeType.FUMBLE, player_id=self.opp_player_id, opp_player_id=self.player_id))

        return True
