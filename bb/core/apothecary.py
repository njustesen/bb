from core import Procedure, Casualty
from model import Outcome, OutcomeType, Rules, ActionType, DiceRoll, D6, D8, PlayerState
from enum import Enum


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
    """
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
    """
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
                n = min(61, max(38, result))
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