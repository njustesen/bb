from procs.procedure import Procedure
from model.outcome import *
from model.action import *
from model.player import *
from model.exceptions import *
from procs.procedure import Procedure
from model.action import Action, ActionType
from model.outcome import Outcome, OutcomeType
from procs.move_action import MoveAction


class TurnStunned(Procedure):

    def __init__(self, game, home):
        self.game = game
        self.home = home
        super().__init__()

    def step(self, action):
        players = []
        player_states = self.game.state.get_team_state(self.home).player_states
        for player_id in player_states.keys():
            if player_states[player_id] == PlayerState.STUNNED:
                self.game.state.get_team_state(self.home).player_states[player_id] = PlayerState.DOWN_USED
                players.append(player_id)
        return Outcome(OutcomeType.STUNNED_TURNED, n=players), True


class Turn(Procedure):

    turnover_outcomes = [OutcomeType.INTERCEPTION, OutcomeType.INCOMPLETE_PASS, OutcomeType.FAILED_DODGE,
                         OutcomeType.FAILED_GFI, OutcomeType.FAILED_PICKUP, OutcomeType.INCOMPLETE_HANDOFF]

    def __init__(self, game, home, blitz=False, quick_snap=False):
        self.game = game
        self.home = home
        self.procedures = []
        self.procedures.append(TurnStunned(self.game, self.home))
        self.blitz = blitz
        self.quick_snap = quick_snap
        self.blitz_available = not quick_snap
        self.passed = not quick_snap
        self.handoff = not quick_snap
        self.game.state.reset_turn(self.home)
        self.game.state.get_team_state(home).turn += 1
        super().__init__()

    def step(self, action):
        if len(self.procedures) > 0:
            outcome, terminal = self.procedures[0].step(action)
            if outcome.terminal:
                self.procedures.pop()
                if outcome.outcome_type == OutcomeType.END_TURN:
                    return outcome, True
                if outcome.outcome_type == OutcomeType.TOUCHDOWN:
                    return outcome, True
                if outcome.outcome_type in Turn.turnover_outcomes:
                    return outcome, True
            return outcome, False
        else:
            if action.action_type == ActionType.START_MOVE:
                player_state = self.game.state.get_player_state(action.player_from_id, self.home)
                if player_state in [PlayerState.DOWN_READY, PlayerState.READY]:
                    self.procedures.insert(0, MoveAction(self.game, self.home, action.player_from_id))
                    return Outcome(OutcomeType.MOVE_ACTION_STARTED, player_id=action.player_from_id)
