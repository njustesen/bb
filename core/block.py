from core import Procedure, KnockDown, Turnover, Push
from model import Skill, Outcome, OutcomeType, DiceRoll, BBDieResult, BBDie, D6, ActionType
from exception import IllegalActionExcpetion


class Block(Procedure):

    def __init__(self, game, home, player_from, pos_from, player_to, pos_to, blitz=False, frenzy_used=False):
        super().__init__(game)
        self.home = home
        self.player_from = player_from
        self.player_to = player_to
        self.pos_from = pos_from
        self.pos_to = pos_to
        self.reroll_used = False
        self.roll = None
        self.blitz = blitz
        self.waiting_wrestle_from = False
        self.waiting_wrestle_to = False
        self.selected_die = None
        self.wrestle = False
        self.favor = None
        self.dauntless_roll = None
        self.dauntless_success = False
        self.frenzy_used = frenzy_used
        self.frenzy_check = False

    def step(self, action):

        if self.frenzy_used and not self.frenzy_check:
            # Check if player was not pushed out of bounds
            if self.game.state.field.get_player_position(self.player_to.player_id) is None:
                return True
            self.game.report(Outcome(OutcomeType.FRENZY_USED, player_id=self.player_from.player_id,
                                     opp_player_id=self.player_to.player_id, team_home=self.home))
            self.frenzy_check = True

        if self.roll is None:

            # Determine dice and favor
            st_from = self.player_from.get_st()
            st_to = self.player_to.get_st()

            # Horns
            if self.blitz and self.player_from.has_skill(Skill.HORNS):
                st_from += 1

            # Dauntless
            if st_to > st_from and self.player_from.has_skill(Skill.DAUNTLESS) and self.dauntless_roll is None:
                self.dauntless_roll = DiceRoll([D6()])
                self.dauntless_success = self.dauntless_roll.get_sum() + st_from > st_to
                self.game.report(Outcome(OutcomeType.DAUNTLESS_USED, team_home=self.home, player_id=self.player_from.id, rolls=[self.dauntless_roll], n=True))
                return False
            elif self.dauntless_roll is not None and self.dauntless_success:
                st_from = st_to

            # Assists
            assists_from = self.game.state.field.assists(self.home, self.player_from, self.player_to)
            assists_to = self.game.state.field.assists(not self.home, self.player_to, self.player_from)
            st_from = st_from + assists_from
            st_to = st_to + assists_to

            # Determine dice and favor
            dice = 0
            if st_from * 2 < st_to:
                dice = 3
                self.favor = not self.home
            elif st_from < st_to:
                dice = 2
                self.favor = not self.home
            elif st_from == st_to:
                dice = 1
                self.favor = self.home
            elif st_from > st_to * 2:
                dice = 3
                self.favor = self.home
            elif st_from > st_to:
                dice = 2
                self.favor = self.home

            # Roll
            self.roll = DiceRoll([])
            for i in range(dice):
                self.roll.dice.append(BBDie())

            return False

        elif self.waiting_wrestle_to and action.team_home != self.home:

            self.wrestle = action.action_type == ActionType.USE_WRESTLE
            self.waiting_wrestle_to = False
            self.selected_die = BBDieResult.BOTH_DOWN

        else:

            # Re-roll
            if action.action_type == ActionType.USE_REROLL:
                if self.reroll_used or not self.game.state.can_use_reroll(self.home):
                    raise IllegalActionExcpetion("Team can't use re-roll")

                # Roll again
                self.reroll_used = True
                self.game.state.get_team_state(self.home).use_reroll()
                return self.step(None)

            # Juggernaut - change 'both down' to 'push'
            if action.action_type == ActionType.USE_JUGGERNAUT:

                if not self.player_from.has_skill(Skill.JUGGERNAUT):
                    raise IllegalActionExcpetion("Player does not have the Juggernaut skill")

                if not self.blitz:
                    raise IllegalActionExcpetion("Juggernaut can only be used in blitz actions")

                if not self.roll.contains(BBDieResult.BOTH_DOWN):
                    raise IllegalActionExcpetion("Dice is not 'both down'")

                self.selected_die = BBDieResult.PUSH

            # Wrestle
            if action.action_type == ActionType.USE_WRESTLE:

                if not self.player_to.has_skill(Skill.WRESTLE):
                    raise IllegalActionExcpetion("Player does not have the Wrestle skill")

                if not self.roll.contains(BBDieResult.BOTH_DOWN):
                    raise IllegalActionExcpetion("Roll does not contain 'Both Down'")

                self.wrestle = True

            # Select dice
            if not self.wrestle:

                if action.action_type == ActionType.SELECT_DIE:

                    if (action.team_home != self.home and self.favor) or (action.team_home == self.home and not self.favor):
                        raise IllegalActionExcpetion("The other team has to select a die")

                    die = self.roll.dice[action.idx]

                    if die.get_value() == BBDieResult.ATTACKER_DOWN:
                        self.selected_die = BBDieResult.ATTACKER_DOWN

                    if die.get_value == BBDieResult.BOTH_DOWN:

                        # Wrestle - opponent
                        if self.player_to.has_skill(Skill.WRESTLE) and \
                                not (self.player_from.has_skill(Skill.JUGGERNAUT) and self.blitz):
                            self.waiting_wrestle_to = True

                    return True

        # Effect
        if self.wrestle:
            if self.game.state.field.has_ball(self.player_from.id):
                Turnover(self.game, self.home)
            KnockDown(self.game, self.home, self.player_from.id, opp_player_id=self.player_to.id, armor_roll=False, injury_roll=False, both_down=True)
            return True

        if self.selected_die == BBDieResult.ATTACKER_DOWN:
            Turnover(self.game, self.home)
            KnockDown(self.game, self.home, self.player_from.id, opp_player_id=self.player_to.id)
            return True

        if self.selected_die == BBDieResult.BOTH_DOWN:
            if not self.player_from.has_skill(Skill.BLOCK):
                Turnover(self.game, self.home)
                if not self.player_to.has_skill(Skill.BLOCK):
                    KnockDown(self.game, self.home, self.player_from.id, opp_player_id=self.player_to.id, both_down=True)
                else:
                    KnockDown(self.game, self.home, self.player_from.id, opp_player_id=self.player_to.id, both_down=False)
            elif not self.player_to.has_skill(Skill.BLOCK):
                KnockDown(self.game, self.home, self.player_to.id, opp_player_id=self.player_from.id)
            elif self.player_from.has_skill(Skill.FRENZY) and not self.frenzy_used:
                # GFI
                Block(self.game, self.home, self.player_from, self.pos_from, self.player_to, blitz=self.blitz, frenzy_used=True)
            return True

        if self.selected_die == BBDieResult.DEFENDER_DOWN:
            Push(self.game, self.home, self.player_to, player_to=self.player_from, knock_down=True, blitz=self.blitz)
            return True

        if self.selected_die == BBDieResult.DEFENDER_STUMBLES:
            if not self.player_to.has_skill(Skill.DODGE):
                Push(self.game, self.home, self.player_to, player_to=self.player_from.id, knock_down=True, blitz=self.blitz)
            elif self.player_from.has_skill(Skill.FRENZY) and not self.frenzy_used:
                # GFI?
                Block(self.game, self.home, self.player_from, self.pos_from, self.player_to, blitz=self.blitz, frenzy_used=True)
            return True

        if self.selected_die == BBDieResult.PUSH:
            if self.player_from.has_skill(Skill.FRENZY) and not self.frenzy_used:
                # GFI?
                Block(self.game, self.home, self.player_from, self.pos_from, self.player_to, blitz=self.blitz, frenzy_used=True)
            Push(self.game, self.home, self.player_to, player_to=self.player_from.id, knock_down=False, blitz=self.blitz)

            return True
        return False