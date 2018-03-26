from core import Procedure
from model import Outcome, OutcomeType, ActionType, PlayerState, PlayerActionType, PlayerAction
from exception import IllegalActionExcpetion


class Turnover(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.home = home

    def step(self, action):
        self.game.report(Outcome(OutcomeType.TURNOVER, team_home=self.home))
        return True


class Touchdown(Procedure):

    def __init__(self, game, home, player_id):
        super().__init__(game)
        self.game = game
        self.home = home
        self.player_id = player_id

    def step(self, action):
        self.game.report(Outcome(OutcomeType.TOUCHDOWN, team_home=self.home, player_id=self.player_id))
        return True


class TurnStunned(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.home = home

    def step(self, action):
        players = []
        player_states = self.game.state.get_team_state(self.home).player_states
        for player_id in player_states.keys():
            if player_states[player_id] == PlayerState.STUNNED:
                self.game.state.get_team_state(self.home).player_states[player_id] = PlayerState.DOWN_USED
                players.append(player_id)
        self.game.report(Outcome(OutcomeType.STUNNED_TURNED, n=players))
        return True


class Turn(Procedure):

    start_actions = [ActionType.START_MOVE, ActionType.START_BLITZ, ActionType.START_BLOCK, ActionType.START_MOVE,
                     ActionType.START_FOUL, ActionType.START_PASS, ActionType.START_HANDOFF]

    def __init__(self, game, home, blitz=False, quick_snap=False):
        super().__init__(game)
        self.home = home
        self.blitz = blitz
        self.quick_snap = quick_snap
        self.blitz_available = not quick_snap
        self.pass_available = not quick_snap
        self.handoff_available = not quick_snap
        self.game.state.reset_turn(self.home)
        self.game.state.get_team_state(home).turn += 1
        self.pass_action_taken = False
        self.blitz_action_taken = False
        self.foul_action_taken = False
        TurnStunned(self.game, self.home)

    def start_player_action(self, outcome_type, player_action_type, player_id):

        # Start action
        PlayerAction(self.game, self.home, player_id, player_action_type, turn=self)
        self.game.report(Outcome(outcome_type, player_id=player_id))
        return False

    def step(self, action):

        # Handle End Turn action
        if action.action_type == ActionType.END_TURN:
            self.game.report(Outcome(OutcomeType.END_OF_TURN, team_home=self.home))
            return True

        # Handle Start Move action
        if action.action_type in Turn.start_actions:
            player_state = self.game.state.get_player_state(action.player_from_id, self.home)

            # Is player ready
            if player_state not in [PlayerState.DOWN_READY, PlayerState.READY]:
                raise IllegalActionExcpetion("Player is not ready to take an action")

            # Start movement action
            if action.action_type == ActionType.START_MOVE:
                return self.start_player_action(OutcomeType.MOVE_ACTION_STARTED, PlayerActionType.MOVE, action.player_from_id)

            # Start blitz action
            if action.action_type == ActionType.START_BLITZ and not self.blitz_action_taken:
                self.blitz_action_taken = True
                return self.start_player_action(OutcomeType.BLITZ_ACTION_STARTED, PlayerActionType.BLITZ, action.player_from_id)

            # Start foul action
            if action.action_type == ActionType.START_FOUL and not self.foul_action_taken:
                self.foul_action_taken = True
                return self.start_player_action(OutcomeType.FOUL_ACTION_STARTED, PlayerActionType.FOUL, action.player_from_id)

            # Start block action
            if action.action_type == ActionType.START_BLOCK:
                return self.start_player_action(OutcomeType.BLOCK_ACTION_STARTED, PlayerActionType.BLOCK, action.player_from_id)

            # Start pass action
            if action.action_type == ActionType.START_PASS and not self.pass_action_taken:
                self.pass_action_taken = True
                return self.start_player_action(OutcomeType.PASS_ACTION_STARTED, PlayerActionType.PASS, action.player_from_id)

            # Start handoff action
            if action.action_type == ActionType.START_HANDOFF:
                return self.start_player_action(OutcomeType.HANDOFF_ACTION_STARTED, PlayerActionType.HANDOFF, action.player_from_id)

        raise IllegalActionExcpetion("Unknown action")

