from procs.procedure import Procedure
from procs.knock_down import *
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


class Move(Procedure):

    def __init__(self, game, home, player_id, from_pos, to_pos, gfi, dodge):
        self.game = game
        self.home = home
        self.player_id = player_id
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.procedures = []
        if gfi:
            self.procedures.append(GFI(game, home, player_id, from_pos, to_pos))
        if dodge:
            self.procedures.append(Dodge(game, home, player_id, from_pos, to_pos))
        super().__init__()

    def step(self, action):

        self.game.state.field.move(self.from_pos, self.to_pos)

        if len(self.procedures) > 0:
            outcome, terminal = self.procedures[0].step(action)
            if outcome.terminal:
                self.procedures.pop()
                return outcome, True
            return outcome, False


class GFI(Procedure):

    def __init__(self, game, home, player_id, from_pos, to_pos):
        self.game = game
        self.home = home
        self.player_id = player_id
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.procedures = []
        self.awaiting_reroll = False
        self.awaiting_sure_feet = False
        self.sure_feet_used = False
        self.reroll_used = False
        self.rolled = False
        super().__init__()

    def step(self, action):

        # Check if nested procedures
        if len(self.procedures) > 0:
            outcome, terminal = self.procedures[0].step(action)
            if outcome.terminal:
                self.procedures.pop()
                return outcome, True
            return outcome, False

        # Otherwise roll if player hasn't
        if action is None and not self.rolled:

            # Roll
            roll = DiceRoll([D6()])
            self.rolled = True

            if roll.get_sum() == 6:
                # Success
                return Outcome(OutcomeType.SUCCESSFUL_GFI, player_id=self.player_id, pos=self.to_pos), True
            else:
                # Check if sure feet
                player = self.game.get_player(self.player_id)
                if player.has_skill(Skill.SURE_FEET) and not self.sure_feet_used:
                    self.sure_feet_used = True
                    self.awaiting_sure_feet = True
                    return Outcome(OutcomeType.FAILED_GFI, player_id=self.player_id, pos=self.to_pos, rolls=[roll]), False

                # Check if reroll available
                if self.game.state.can_use_reroll(self.home) and not self.sure_feet_used:
                    self.awaiting_reroll = True
                    return Outcome(OutcomeType.FAILED_GFI, player_id=self.player_id, pos=self.to_pos, rolls=[roll]), False

                # Add knockdown proc
                self.procedures.append(KnockDown(self.game, self.home, self.player_id, self.to_pos))
                return Outcome(OutcomeType.FAILED_GFI, player_id=self.player_id, pos=self.to_pos), False

        # If sure feet used
        if self.awaiting_sure_feet:
            if action.action_type == ActionType.USE_SKILL:
                self.sure_feet_used = True
                self.rolled = False
                self.step(None)
            else:
                return Outcome(OutcomeType.FAILED_GFI, player_id=self.player_id, pos=self.to_pos), True

        # If reroll used
        if self.awaiting_reroll:
            if action.action_type == ActionType.USE_REROLL:
                self.reroll_used = True
                self.game.state.get_team_state(self.home).reroll_used = True
                self.game.state.get_team_state(self.home).rerolls -= 1
                self.rolled = False
                self.step(None)
            else:
                return Outcome(OutcomeType.FAILED_GFI, player_id=self.player_id, pos=self.to_pos), True



class Dodge(Procedure):

    def __init__(self, game, home, player_id, from_pos, to_pos):
        self.game = game
        self.home = home
        self.player_id = player_id
        self.from_pos = from_pos
        self.to_pos = to_pos
        super().__init__()

    def step(self, action):
        # TODO:


class Fumble(Procedure):

    def __init__(self, game, home, player_id, pos):
        self.game = game
        self.home = home
        self.player_id = player_id
        self.pos = pos
        super().__init__()

    def step(self, action):



class PlayerAction(Procedure):

    failed_outcomes = [OutcomeType.FAILED_GFI, OutcomeType.FAILED_DODGE, OutcomeType.TOUCHDOWN,
                       OutcomeType.FAILED_PICKUP, OutcomeType.BALL_DROPPED]

    def __init__(self, game, home, player_id, type):
        self.game = game
        self.home = home
        self.player_id = player_id
        self.moves = 0
        self.procedures = []
        self.type = type
        super().__init__()

    def step(self, action):

        if len(self.procedures) > 0:
            outcome, terminal = self.procedures[0].step(action)
            if outcome.terminal:
                self.procedures.pop()
            if outcome.outcome_type in PlayerAction.failed_outcomes:
                return outcome, True
            if outcome.terminal and self.game.state.get_player_state(self.player_id, self.home) != PlayerState.READY:
                return outcome, True
            return outcome, False

        if action.action_type == ActionType.END_PLAYER_TURN:
            return Outcome(OutcomeType.END_PLAYER_TURN), True

        if action.action_type == ActionType.MOVE:
            position = self.game.state.field.get_player_position(player_id=action.player_from_id)
            player = self.game.get_team(self.home).get_player_by_id(action.player_from_id)
            player_state = self.game.state.get_player_state(action.player_id, self.home)

            # Check if ready
            if player_state not in [PlayerState.READY, PlayerState.DOWN_READY]:
                raise IllegalActionExcpetion("Player is not ready")

            # Check if square is nearby
            if not self.game.arena.is_neighbor(position, action.pos_to):
                raise IllegalActionExcpetion("Square is not nearby")

            # Check if square is empty
            if self.game.field.get_player_id_at(action.pos_to) is not None:
                raise IllegalActionExcpetion("Square is occupied")

            # Check GFI
            move_needed = 3 if player_state == PlayerState.DOWN_READY else 1
            gfi_allowed = 3 if player.has_skill(Skill.SPRINT) else 2
            if self.moves + move_needed > player.get_ma() + gfi_allowed:
                raise IllegalActionExcpetion("No movement points left")

            gfi = self.moves + move_needed > player.get_ma()
            self.procedures.insert(0, Move(self.game, self.home, self.player_id, position, action.pos_to, gfi))