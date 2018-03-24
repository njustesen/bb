from core import Procedure
from model import Outcome, OutcomeType, ActionType, PlayerState, PlayerActionType, PlayerAction


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
        TurnStunned(self.game, self.home)

    def step(self, action):
        # Handle End Turn action
        if action.action_type == ActionType.END_TURN:
            self.game.report(Outcome(OutcomeType.END_OF_TURN, team_home=self.home))
            return True

        # Handle Start Move action
        if action.action_type == ActionType.START_MOVE:
            player_state = self.game.state.get_player_state(action.player_from_id, self.home)
            if player_state in [PlayerState.DOWN_READY, PlayerState.READY]:
                PlayerAction(self.game, self.home, action.player_from_id, PlayerActionType.MOVE)
                self.game.report(Outcome(OutcomeType.MOVE_ACTION_STARTED, player_id=action.player_from_id))
                return False

