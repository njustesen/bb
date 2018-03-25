from core import Procedure, Injury, Turnover, Ejection
from model import Outcome, OutcomeType, DiceRoll, D6, Skill


class Armor(Procedure):

    def __init__(self, game, home, player_id, modifiers=0, opp_player_id=None, foul=False):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.modifiers = modifiers
        self.opp_player_id = opp_player_id
        self.skip_armor = False
        self.armor_rolled = False
        self.player = game.get_player(player_id)
        self.foul = foul
        self.opp_player = None
        if self.opp_player_id is not None:
            self.opp_player = game.get_player(opp_player_id)

    def step(self, action):

        # Roll
        roll = DiceRoll(D6(), D6())
        roll.modifiers = self.modifiers
        result = roll.get_sum() + self.modifiers
        self.armor_rolled = True

        armor_broken = False
        mighty_blow_used = False
        dirty_player_used = False

        if not self.foul:
            # Armor broken - Claws
            if result >= 8 and self.opp_player is not None and self.opp_player.has_skill(Skill.CLAWS):
                armor_broken = True

            # Armor broken
            if result > self.player.get_av():
                armor_broken = True

            # Armor broken - Might Blow
            if self.opp_player is not None and self.opp_player.has_skill(Skill.MIGHTY_BLOW) and result + 1 > self.player.get_av():
                roll.modifiers += 1
                armor_broken = True
                mighty_blow_used = True
        else:

            # Armor broken - Dirty player
            if self.opp_player is not None and self.opp_player.has_skill(Skill.DIRTY_PLAYER) and result + 1 > self.player.get_av():
                roll.modifiers += 1
                armor_broken = True
                dirty_player_used = True

            # Armor broken
            if result > self.player.get_av():
                armor_broken = True

        # Referee
        ejected = False
        if self.foul:
            if roll.same():
                if not (self.opp_player.has_skill(Skill.SNEAKY_GIT) and not armor_broken):
                    self.game.report(Outcome(OutcomeType.PLAYER_EJECTED, player_id=self.opp_player_id))
                    Turnover(self.game, self.home)
                    Ejection(self.game, self.home, self.player_id)
                    ejected = True

        # Break armor - roll injury
        if armor_broken:
            Injury(self.game, self.home, self.player_id, self.opp_player_id, foul=self.foul,
                   mighty_blow_used=mighty_blow_used, dirty_player_used=dirty_player_used, ejected=ejected)
            self.game.report(Outcome(OutcomeType.ARMOR_BROKEN, player_id=self.player_id,
                                     opp_player_id=self.opp_player_id, rolls=[roll]))
        else:
            self.game.report(Outcome(OutcomeType.ARMOR_NOT_BROKEN, player_id=self.player_id,
                                     opp_player_id=self.opp_player_id,  rolls=[roll]))


        return True