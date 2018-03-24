from procs.procedure import Procedure
from procs.knock_down import *
from procs.turn import *
from model.outcome import *
from model.action import *
from model.player import *
from model.exceptions import *
from model.action import Action, ActionType
from model.outcome import Outcome, OutcomeType
from model.dice import *
from enum import Enum


class PlayerActionType(Enum):
    MOVE = 1
    BLOCK = 2
    BLITZ = 3
    PASS = 4
    HANDOFF = 5
    FOUL = 7


class Block(Procedure):

    def __init__(self, game, home, player_from, pos_from, player_to, pos_to):
        super().__init__(game)
        self.home = home
        self.player_from = player_from
        self.player_to = player_to
        self.pos_from = pos_from
        self.pos_to = pos_to
        self.reroll_used = False
        self.roll = None

    def step(self, action):

        if self.roll is None:

            # Determine dice and favor
            st_from = self.player_from.get_st() + self.game.state.field.assists(self.player_from, self.player_to)
            st_to = self.player_to.get_st() + self.game.state.field.assists(self.player_to, self.player_from)

            # Determine dice and favor
            dice = 0
            favor = None
            if st_from * 2 < st_to:
                dice = 3
                favor = not self.home
            elif st_from < st_to:
                dice = 2
                favor = not self.home
            elif st_from == st_to:
                dice = 1
            elif st_from > st_to * 2:
                dice = 3
                favor = self.home
            elif st_from > st_to:
                dice = 2
                favor = self.home

            # Roll
            self.roll = DiceRoll([])
            for i in range(dice):
                self.roll.dice.append(BBDie())

        else:

            # Re-roll
            if action.action_type == ActionType.USE_REROLL:

                if self.reroll_used or not self.game.state.can_use_reroll(self.home):
                    raise IllegalActionExcpetion("Team can't use re-roll")

                # Roll again
                self.reroll_used = True
                self.game.state.get_team_state(self.home).use_reroll()
                return self.step(None)

            # Select dice
            if action.action_type == ActionType.SELECT_DIE:
                die = self.roll.dice[action.idx]
                if die.get_value() == BBDieResult.ATTACKER_DOWN:
                    Turnover(self.game, self.home)
                    KnockDown(self.game, self.home, self.player_from.id, opp_player_id=self.player_to.id)
                    return True

                if die.get_value == BBDieResult.BOTH_DOWN:
                    if not self.player_from.has_skill(Skill.BLOCK):
                        Turnover(self.game, self.home)
                        KnockDown(self.game, self.home, self.player_from.id, opp_player_id=self.player_to.id)
                    if not self.player_to.has_skill(Skill.BLOCK):
                        KnockDown(self.game, self.home, self.player_to.id, opp_player_id=self.player_from.id)


        return False


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
        self.game.state.field.move(self.from_pos, self.to_pos)
        if self.game.arena.is_touchdown(self.to_pos, not self.home):
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

            if roll.get_sum() == 6:

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

            mod_ag = max(0, min(attribute + modifiers, 10))
            target = Dodge.success[mod_ag]

            if roll.get_sum() == target:

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


class PlayerAction(Procedure):

    def __init__(self, game, home, player_id, type):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.moves = 0
        self.type = type

    def step(self, action):

        if action.action_type == ActionType.END_PLAYER_TURN:
            return Outcome(OutcomeType.END_PLAYER_TURN), True

        # Action attributes
        player_from = self.game.get_team(self.home).get_player_by_id(action.player_from_id)
        player_to = self.game.get_team(self.home).get_player_by_id(action.player_to_id)

        player_state_from = self.game.state.get_player_state(action.player_id, self.home)
        player_state_to = None
        if player_to is not None:
            player_state_to = self.game.state.get_player_state(action.player_to_id, self.home)

        if action.action_type == ActionType.MOVE:

            # Check if action is allowed
            if self.type == PlayerActionType.BLOCK or self.type == PlayerActionType.FOUL:
                raise IllegalActionExcpetion("Players cannot move if they are doing a block of foul player action")

            # Check if ready
            if player_state_from not in [PlayerState.READY, PlayerState.DOWN_READY]:
                raise IllegalActionExcpetion("Player is not ready")

            # Check if square is nearby
            if not self.game.arena.is_neighbor(action.pos_from, action.pos_to):
                raise IllegalActionExcpetion("Square is not nearby")

            # Check if square is empty
            if self.game.field.get_player_id_at(action.pos_to) is not None:
                raise IllegalActionExcpetion("Square is occupied")

            # Check GFI
            move_needed = 3 if player_state_from == PlayerState.DOWN_READY else 1
            gfi_allowed = 3 if player_from.has_skill(Skill.SPRINT) else 2
            if self.moves + move_needed > player_from.get_ma() + gfi_allowed:
                raise IllegalActionExcpetion("No movement points left")

            # Check dodge
            if self.game.get_player(self.player_id).has_skill(Skill.BALL_AND_CHAIN):
                # Ball and chain -> Auto-dodge
                dodge = True
            else:
                tackle_zones_from = self.game.state.field.get_tackle_zones(action.pos_from, self.home)
                dodge = tackle_zones_from > 0

            # Check GFI
            gfi = self.moves + move_needed > player_from.get_ma()

            # Add proc
            Move(self.game, self.home, self.player_id, action.pos_from, action.pos_to, gfi, dodge)
            self.moves += move_needed

        elif action.action_type == ActionType.BLOCK:

            # Check if action is allowed
            if self.type != PlayerActionType.BLOCK or self.type != PlayerActionType.BLITZ:
                raise IllegalActionExcpetion("Players cannot block if they are not doing a block of blitz player action")

            # Add proc
            Block(self.game, self.home, player_from, action.pos_from, player_to, action.pos_to)