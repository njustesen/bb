from bb.core.procedure import *
import json
import pickle


class Game:

    def __init__(self, game_id, home, away, arena, config, state=None):
        self.game_id = game_id
        self.home = home
        self.away = away
        self.arena = arena
        self.stack = Stack()
        self.reports = []
        self.config = config
        self.game_over = False
        self.available_actions = []
        self.state = state if state is not None else GameState(self)

    def _squares_moved(self):
        for proc in self.stack.items:
            if isinstance(proc, PlayerAction):
                out = []
                for square in proc.squares:
                    out.append(square.to_simple())
                return out
        return []

    def to_simple(self):
        available_actions = []
        for action in self.available_actions:
            available_actions.append(action.to_simple())
        reports = []
        for report in self.reports:
            reports.append(report.to_simple())
        return {
            'game_id': self.game_id,
            'home_team': self.home.to_simple(),
            'away_team': self.away.to_simple(),
            'state': self.state.to_simple(),
            'game_over': self.game_over,
            'stack': self.procs(),
            'available_actions': available_actions,
            'reports': reports,
            'squares_moved': self._squares_moved(),
            'arena': self.arena.to_simple()
        }

    def init(self):
        EndGame(self)
        Pregame(self)
        self.set_available_actions()
        # self.step(None)

    def _action_allowed(self, action):
        print(action.to_simple())
        if action is None:
            return True
        for action_choice in self.available_actions:
            if action.action_type == action_choice.action_type:
                if len(action_choice.player_ids) > 0 and action.player_from_id is not None and action.player_from_id not in action_choice.player_ids:
                    print("Illegal player_id")
                    return False
                if len(action_choice.positions) > 0 and action.pos_to is not None and action.pos_to not in action_choice.positions:
                    print("Illegal position")
                    return False
                if len(action_choice.indexes) > 0 and action.idx is not None and action.idx >= 0 and action.idx not in action_choice.indexes:
                    print("Illegal index")
                    return False
                break
        return True

    def step(self, action):
        """
        Executes one step in the game. If in Fast Mode, it executes several steps until action is required.
        :param action: Action from agent. Can be None if no action is required.
        :return: True if game requires action or game is over, False if not
        """

        # Get proc
        proc = self.stack.peek()

        # If no action and action is required
        self.available_actions = proc.available_actions()
        if action is None and len(self.available_actions) > 0:
            return True

        # If action but it's not available
        if action is not None:
            if action.action_type == ActionType.CONTINUE:
                if len(self.available_actions) == 0:
                    # Consider this as no action
                    action.action_type = None
                else:
                    return True
            else:
                # Only allow
                if not self._action_allowed(action):
                    print("Action not allowed! ", action.action_type)
                    return True

        # Run proc
        print("Proc={}".format(proc))
        print("Action={}".format(action.action_type if action is not None else ""))
        proc.done = proc.step(action)
        print("Done={}".format(proc.done))


        # Enable if cloning happens
        for player_id, pos in self.state.field.player_positions.items():
            if self.state.field.board[pos.y][pos.x] != player_id:
                raise Exception(pos.to_simple() + ": " + player_id )

        for y in range(len(self.state.field.board)):
            for x in range(len(self.state.field.board[0])):
                assert self.state.field.board[y][x] is None or (self.state.field.player_positions[self.state.field.board[y][x]].x == x and self.state.field.player_positions[self.state.field.board[y][x]].y == y)

        # Remove all finished procs
        if proc.done:
            while not self.stack.is_empty() and self.stack.peek().done:
                print("--Proc={}".format(self.stack.peek()))
                self.stack.pop()

            # Is game over
            if self.stack.is_empty():
                return False

        print("-Proc={}".format(self.stack.peek()))

        # Update available actions
        self.set_available_actions()
        if len(self.available_actions) == 0:
            # We can continue without user input
            return False

        # End player turn if only action available
        if len(self.available_actions) == 1 and self.available_actions[0].action_type == ActionType.END_PLAYER_TURN:
            self.step(Action(ActionType.END_PLAYER_TURN, player_from_id=self.available_actions[0].player_ids[0]))
            # We can continue without user input
            return False

        # Game needs user input
        return True

    def set_available_actions(self):
        self.available_actions = self.stack.peek().available_actions()
        assert(self.available_actions is not None)

    def report(self, outcome):
        print(outcome.outcome_type.name)
        #print(json.dumps(outcome.to_simple()))
        self.reports.append(outcome)

    def get_team(self, home):
        return self.home if home else self.away

    def get_player(self, player_id):
        if self.get_home_by_player_id(player_id):
            return self.home.get_player_by_id(player_id)
        return self.away.get_player_by_id(player_id)

    def get_home_by_player_id(self, player_id):
        if self.home.has_player_by_id(player_id):
            return True
        return False

    def get_team_by_player_id(self, player_id):
        if self.home.has_player_by_id(player_id):
            return self.home
        return self.away

    def is_on_home_team(self, player_id):
        if self.home.has_player_by_id(player_id):
            return True
        return False

    def is_on_team(self, player_id, home):
        if self.home.has_player_by_id(player_id):
            return home
        return not home

    def procs(self):
        procs = []
        for proc in self.stack.items:
            if isinstance(proc, Turn) and proc.quick_snap:
                procs.append("QuickSnap")
            elif isinstance(proc, Turn) and proc.blitz:
                procs.append("Blitz")
            else:
                procs.append(proc.__class__.__name__)
        return procs
