from bb.core.procedure import *
import json
import pickle


class Game:

    def __init__(self, game_id, home, away, arena, config, state=None):
        self.game_id = game_id
        self.home = home
        self.away = away
        self.arena = arena
        self.state = state
        self.stack = Stack()
        self.reports = []
        self.config = config
        self.game_over = False
        self.available_actions = []
        self.last_turn = None

        if self.state is None:
            self.state = GameState(self)

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
        Pregame(self)
        self.set_available_actions()
        self.step(None)

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

        # If touchdown, end turn and add kickoff
        if isinstance(self.stack.peek(), Touchdown):
            self._touchdown(self.stack.peek())

        # If turnover, end turn
        if isinstance(self.stack.peek(), Turnover):
            self.stack.peek().step(None)
            self._end_turn()

        # If riot -> remove one turn
        if isinstance(self.stack.peek(), Riot):
            if self.stack.peek().effect == 1:
                self._add_turn()
            elif self.stack.peek().effect == -1:
                self._remove_turn()

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

        ''' Enable if cloning happens
        for player_id, pos in self.state.field.player_positions.items():
            assert self.state.field.board[pos.y][pos.x] == player_id

        for y in range(len(self.state.field.board)):
            for x in range(len(self.state.field.board[0])):
                assert self.state.field.board[y][x] is None or (self.state.field.player_positions[self.state.field.board[y][x]].x == x and self.state.field.player_positions[self.state.field.board[y][x]].y == y)
        '''

        # Remove done procs
        if proc.done:

            # Clear done procs
            while not self.stack.is_empty() and self.stack.peek().done:

                print("--Proc={}".format(self.stack.peek()))

                # If Half is done
                if isinstance(proc, Half):
                    if proc.half == 1:
                        self.state.half = self.stack.peek().half + 1
                        self.state.home_state.turn = 0
                        self.state.away_state.turn = 0
                    self.stack.pop()

                # If pre-game is over
                elif isinstance(self.stack.peek(), Pregame):
                    self.stack.pop()
                    Half(self, 2)
                    Half(self, 1)
                    self.state.half = 1
                    self.state.home_state.turn = 0
                    self.state.away_state.turn = 0
                elif isinstance(self.stack.peek(), Half):
                    self.stack.pop()
                    self.state.half += 1
                else:
                    self.stack.pop()

            # Is game over
            if self.stack.is_empty():
                self.state.team_turn = None
                self.game_over = True
                return False

            # If new turn on stack - set turn and half counters
            if isinstance(self.stack.peek(), Turn) and self.stack.peek() != self.last_turn:
                self.last_turn = self.stack.peek()
                self.state.team_turn = self.stack.peek().home
                if not self.stack.peek().blitz and not self.stack.peek().quick_snap:
                    if self.state.team_turn:
                        self.state.home_state.turn += 1
                        self.report(Outcome(OutcomeType.TURN_START, team_home=True, n=self.state.home_state.turn))
                    elif not self.state.team_turn:
                        self.state.away_state.turn += 1
                        self.report(Outcome(OutcomeType.TURN_START, team_home=False, n=self.state.away_state.turn))

        print("-Proc={}".format(self.stack.peek()))

        # Update available actions
        self.set_available_actions()
        if len(self.available_actions) == 0:
            # We can continue without user input
            return False

        # If player can't do more than end turn
        if len(self.available_actions) == 1 and self.available_actions[0].action_type == ActionType.END_PLAYER_TURN:
            self.step(Action(ActionType.END_PLAYER_TURN, player_from_id=self.available_actions[0].player_ids[0]))
            # We can continue without user input
            return False

        # Game needs user input
        return True

    def set_available_actions(self):
        self.available_actions = self.stack.peek().available_actions()

    def report(self, outcome):
        #print(outcome.outcome_type.name)
        #print(json.dumps(outcome.to_simple()))
        self.reports.append(outcome)

    def _remove_turn(self):
        for idx in range(self.stack.size()):
            if isinstance(self.stack.items[idx], Turn):
                self.stack.items.remove(idx)
                self.stack.items.remove(idx)
                break

    def _add_turn(self):
        for idx in reversed(range(self.stack.size())):
            if isinstance(self.stack.items[idx], Turn):
                home = self.stack.items[idx].home
                self.stack.items.insert(idx, Turn(self, home=home))
                self.stack.items.insert(idx, Turn(self, home=not home))
                break

    def _end_turn(self):
        """
        Removes all procs in the current turn - including the current turn proc.
        """
        x = 0
        for i in reversed(range(self.stack.size())):
            x += 1
            if isinstance(self.stack.items[i], Turn):
                break
        for i in range(x):
            self.stack.pop()

    def _touchdown(self, proc):
        """
        Removes all procs in the current turn - including the current turn proc, and then creates procs to
        prepare for kickoff.
        """
        proc.step(None)
        self._end_turn()
        KickOff(self, proc.home)
        Setup(self, not proc.home)
        Setup(self, proc.home)
        ClearBoard(self)

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
