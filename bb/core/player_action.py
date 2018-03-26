from core import Procedure, Block, Move, Foul, PassAction
from exception import IllegalActionExcpetion
from model import ActionType, Outcome, OutcomeType, Skill, PlayerState, PassDistance, WeatherType
from enum import Enum


class PlayerActionType(Enum):
    MOVE = 1
    BLOCK = 2
    BLITZ = 3
    PASS = 4
    HANDOFF = 5
    FOUL = 7


class PlayerAction(Procedure):

    def __init__(self, game, home, player_id, player_action_type, turn):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.moves = 0
        self.player_action_type = player_action_type
        self.turn = turn

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
            if self.player_action_type == PlayerActionType.BLOCK:
                raise IllegalActionExcpetion("Players cannot move if they are doing a block player action")

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

            return False

        elif action.action_type == ActionType.BLOCK:

            # Check if action is allowed
            if self.player_action_type != PlayerActionType.BLOCK or self.player_action_type != PlayerActionType.BLITZ:
                raise IllegalActionExcpetion("Players cannot block if they are not doing a block of blitz player action")

            if player_state_to == PlayerState.DOWN_READY or player_state_to == PlayerState.DOWN_USED:
                raise IllegalActionExcpetion("Players cannot block opponent players that are down")

            # Check GFI
            gfi = False
            if action.action_type == ActionType.BLITZ:
                move_needed = 1 if player_state_from == PlayerState.DOWN_READY else 1
                gfi_allowed = 3 if player_from.has_skill(Skill.SPRINT) else 2
                if self.moves + move_needed > player_from.get_ma() + gfi_allowed:
                    raise IllegalActionExcpetion("No movement points left")
                gfi = self.moves + move_needed > player_from.get_ma()
                # Use movement
                self.moves += move_needed
                self.game.state.set_player_state(player_from.player_id, self.home, PlayerState.READY)

            # Check frenzy
            if player_from.has_skill(Skill.FRENZY):
                move_needed = 0
                if self.player_action_type == ActionType.BLITZ:
                    move_needed = 1
                gfi_allowed = 3 if player_from.has_skill(Skill.SPRINT) else 2
                if self.moves + move_needed <= player_from.get_ma() + gfi_allowed:
                    gfi_2 = self.moves + move_needed > player_from.get_ma()
                    Block(self.game, self.home, player_from, player_to, action.pos_to, gfi=gfi)
                    gfi = gfi_2  # Switch gfi
                # Use movement
                self.moves += move_needed

            # Block
            Block(self.game, self.home, player_from, player_to, action.pos_to, gfi=gfi)

            return False

        elif action.action_type == ActionType.FOUL:

            if self.player_action_type != ActionType.FOUL:
                raise IllegalActionExcpetion("Fouls can only be done in foul actions")

            if player_state_to not in [PlayerState.DOWN_READY, PlayerState.DOWN_USED, PlayerState.STUNNED]:
                raise IllegalActionExcpetion("Players cannot foul opponent players that are standing")

            Foul(self.game, self.home, player_from, player_to)

            # A foul is a players last thing to do
            return True

        elif action.action_type == ActionType.PASS:

            if self.player_action_type != ActionType.PASS:
                raise IllegalActionExcpetion("Passes can only be done in pass actions")

            if player_state_to not in [PlayerState.READY, PlayerState.USED]:
                raise IllegalActionExcpetion("Passes can only be directed towards standing players")

            if not self.game.state.field.has_ball(player_from.player_id):
                raise IllegalActionExcpetion("Player needs to have ball to pass")

            if not self.turn.pass_available:
                raise IllegalActionExcpetion("Pass is not available in this turn")

            # Check distance
            pos_from = self.game.field.get_player_position(player_from.player_id)
            pass_distance = self.game.field.pass_distance(pos_from, action.pos_to)

            if self.game.state.weather == WeatherType.BLIZZARD:
                if pass_distance != PassDistance.QUICK_PASS or pass_distance != PassDistance.SHORT_PASS:
                    raise IllegalActionExcpetion("Only quick and short passes during blizzards")

            if pass_distance == PassDistance.HAIL_MARY and not player_from.has_skill(Skill.HAIL_MARY):
                raise IllegalActionExcpetion("Hail mary passes requires the Hail Mary skill")

            PassAction(self.game, self.home, player_from, pos_from, player_to, action.pos_to, pass_distance)

            self.turn.pass_available = False
