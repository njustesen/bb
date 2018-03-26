from core import Procedure, KnockDown, Touchdown, Bounce
from model import Skill, Outcome, OutcomeType, DiceRoll, D6, ActionType, WeatherType


class Move(Procedure):

    def __init__(self, game, home, player_id, from_pos, to_pos, gfi, dodge):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.from_pos = from_pos
        self.to_pos = to_pos
        if gfi:
            GFI(game, home, player_id, from_pos, to_pos)
        if dodge:
            Dodge(game, home, player_id, from_pos, to_pos)

    def step(self, action):

        had_ball_before = self.game.state.field.has_ball(self.player_id)
        self.game.state.field.move(self.from_pos, self.to_pos)
        had_ball_after = self.game.state.field.has_ball(self.player_id)

        # Check if player moved onto the ball
        if had_ball_before != had_ball_after:

            # Attempt to pick up the ball - unless no hands
            player = self.game.get_player(self.player_id)
            if player.has_skill(Skill.NO_HANDS):
                Bounce(self.game, self.home)
                return True
            else:
                Pickup(self.game, self.home, self.player_id)
                return True

        elif had_ball_before and self.game.arena.is_touchdown(self.to_pos, self.home):

            # Touchdown if player had the ball with him/her
            Touchdown(self.game, self.home, self.player_id)

        return True


class GFI(Procedure):

    def __init__(self, game, home, player_id, from_pos, to_pos):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.awaiting_reroll = False
        self.awaiting_sure_feet = False
        self.sure_feet_used = False
        self.reroll_used = False
        self.rolled = False

    def step(self, action):

        # If player hasn't rolled
        if not self.rolled:

            # Roll
            roll = DiceRoll([D6()])
            self.rolled = True
            roll.modifiers = 1 if self.game.state.weather == WeatherType.BLIZZARD else 0

            if roll.get_sum() >= 2 + roll.modifiers:

                # Success
                self.game.report(Outcome(OutcomeType.SUCCESSFUL_GFI, player_id=self.player_id, pos=self.to_pos))
                return True

            else:

                # Fail
                self.game.report(Outcome(OutcomeType.FAILED_GFI, player_id=self.player_id, pos=self.to_pos, rolls=[roll]))

                # Check if sure feet
                player = self.game.get_player(self.player_id)
                if player.has_skill(Skill.SURE_FEET) and not self.sure_feet_used:
                    self.sure_feet_used = True
                    self.awaiting_sure_feet = True
                    return False

                # Check if reroll available
                if self.game.state.can_use_reroll(self.home) and not self.sure_feet_used:
                    self.awaiting_reroll = True
                    self.game.report(Outcome(OutcomeType.FAILED_GFI, player_id=self.player_id, pos=self.to_pos, rolls=[roll]))
                    return False

                # Player trips
                KnockDown(self.game, self.home, self.player_id, self.to_pos)
                return True

        # If sure feet used
        if self.awaiting_sure_feet:
            if action.action_type == ActionType.USE_SKILL:
                self.sure_feet_used = True
                self.rolled = False
                self.step(None)
            else:
                # Player trips
                KnockDown(self.game, self.home, self.player_id, self.to_pos)
                return True

        # If reroll used
        if self.awaiting_reroll:
            if action.action_type == ActionType.USE_REROLL:
                # Remove reroll and roll again - recursive call
                self.game.state.get_team_state(self.home).reroll_used = True
                self.game.state.get_team_state(self.home).rerolls -= 1
                self.rolled = False
                self.step(None)
            else:
                # Player trips
                KnockDown(self.game, self.home, self.player_id, self.to_pos)
                return True


class Dodge(Procedure):

    #          0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    success = [6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1]

    def __init__(self, game, home, player_id, from_pos, to_pos):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.player = self.game.get_player(player_id)
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.dodge_used = False
        self.awaiting_dodge = False
        self.awaiting_reroll = False
        self.rolled = False

    def step(self, action):

        # If player hasn't rolled
        if not self.rolled:

            # Check opp skills
            tackle_zones, tackle_id, prehensile_tail_id, diving_tackle_id, shadowing_id, tentacles_id = \
                self.game.state.field.get_tackle_zones_detailed(self.to_pos, self.home)

            # TODO: Allow player to select if shadowing and diving tackle
            # TODO: Put diving tackle or shadowing proc on stack
            # Auto-use other skills

            # Roll
            roll = DiceRoll([D6()])
            self.rolled = True

            # Calculate target
            modifiers = 1
            ignore_opp_mods = False
            if self.player.has_skill(Skill.STUNTY):
                modifiers = 1
                ignore_opp_mods = True
            if self.player.has_skill(Skill.TITCHY):
                modifiers -= 1
                ignore_opp_mods = True
            if self.player.has_skill(Skill.TWO_HEADS):
                modifiers -= 1

            if not ignore_opp_mods:
                modifiers -= tackle_zones

            # Break tackle - use st instead of ag
            attribute = self.player.get_ag()
            if self.player.has_skill(Skill.BREAK_TACKLE) and self.player.get_st() > self.player.get_st():
                attribute = self.player.get_st()

            target = Dodge.success[attribute]
            result = roll.get_sum()
            mod_result = result + roll.modifiers

            if result == 6 or (result != 1 and mod_result >= target):

                # Success
                self.game.report(Outcome(OutcomeType.SUCCESSFUL_DODGE, player_id=self.player_id, pos=self.to_pos))
                return True

            else:

                # Fail
                self.game.report(Outcome(OutcomeType.FAILED_DODGE, player_id=self.player_id, pos=self.to_pos, rolls=[roll]))

                # Check if sure feet
                if self.player.has_skill(Skill.DODGE) and not self.dodge_used:
                    self.dodge_used = True
                    self.awaiting_dodge = True
                    return False

                # Check if reroll available
                if self.game.state.can_use_reroll(self.home) and not self.dodge_used:
                    self.awaiting_reroll = True
                    self.game.report(Outcome(OutcomeType.FAILED_DODGE, player_id=self.player_id, pos=self.to_pos, rolls=[roll]))
                    return False

                # Player trips
                KnockDown(self.game, self.home, self.player_id, self.to_pos)
                return True

        # If sure feet used
        if self.awaiting_dodge:
            if action.action_type == ActionType.USE_SKILL:
                self.dodge_used = True
                self.rolled = False
                self.step(None)
            else:
                # Player trips
                KnockDown(self.game, self.home, self.player_id, self.to_pos)
                return True

        # If reroll used
        if self.awaiting_reroll:
            if action.action_type == ActionType.USE_REROLL:
                # Remove reroll and roll again - recursive call
                self.game.state.get_team_state(self.home).reroll_used = True
                self.game.state.get_team_state(self.home).rerolls -= 1
                self.rolled = False
                self.step(None)
            else:
                # Player trips
                KnockDown(self.game, self.home, self.player_id, self.to_pos)
                return True