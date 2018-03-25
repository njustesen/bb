from core import Procedure, Block, Move
from exception import IllegalActionExcpetion
from model import ActionType, Outcome, OutcomeType, Skill, PlayerState
from enum import Enum


class PlayerActionType(Enum):
    MOVE = 1
    BLOCK = 2
    BLITZ = 3
    PASS = 4
    HANDOFF = 5
    FOUL = 7


class PlayerAction(Procedure):

    def __init__(self, game, home, player_id, action_type):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.moves = 0
        self.action_type = action_type

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
            if self.action_type == PlayerActionType.BLOCK or self.action_type == PlayerActionType.FOUL:
                raise IllegalActionExcpetion("Players cannot move if they are doing a block of foul player action")

            # Check if ready
            if player_state_from not in [PlayerState.READY, PlayerState.DOWN_READY]:
                raise IllegalActionExcpetion("Player is not ready")

            # Check if square is nearby
            if not action.pos_from.is_adjacent(action.pos_to):
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
            if self.action_type != PlayerActionType.BLOCK or self.action_type != PlayerActionType.BLITZ:
                raise IllegalActionExcpetion("Players cannot block if they are not doing a block of blitz player action")

            if player_state_to == PlayerState.DOWN_READY or player_state_to == PlayerState.DOWN_USED:
                raise IllegalActionExcpetion("Players cannot block opponent players that are down")

            # Check GFI
            gfi = False
            if self.action_type == ActionType.BLITZ:
                move_needed = 1 if player_state_from == PlayerState.DOWN_READY else 1
                gfi_allowed = 3 if player_from.has_skill(Skill.SPRINT) else 2
                if self.moves + move_needed > player_from.get_ma() + gfi_allowed:
                    raise IllegalActionExcpetion("No movement points left")
                gfi = self.moves + move_needed > player_from.get_ma()

            # Check frenzy
            if player_from.has_skill(Skill.FRENZY):
                move_needed = 1 if player_state_from == PlayerState.DOWN_READY else 1
                gfi_allowed = 3 if player_from.has_skill(Skill.SPRINT) else 2
                move_needed += 1  # Because its the second block
                if self.moves + move_needed <= player_from.get_ma() + gfi_allowed:
                    gfi_2 = self.moves + move_needed > player_from.get_ma()
                    Block(self.game, self.home, player_from, player_to, action.pos_to, gfi=gfi_2)

            # Block
            Block(self.game, self.home, player_from, player_to, action.pos_to, gfi=gfi)
