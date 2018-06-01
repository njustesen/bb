from bb.core.procedure import *
import json


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

        if self.state is None:
            self.state = GameState(self)

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
        }

    def init(self):
        Pregame(self)
        self.set_available_actions()
        self.step(None)

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
            self._end_turn()

        # If player turn ends
        if isinstance(self.stack.peek(), EndPlayerTurn):
            self._end_player_turn()

        # If riot -> remove one turn
        if isinstance(self.stack.peek(), Riot):
            if self.stack.peek().effect == 1:
                self._add_turn()
            elif self.stack.peek().effect == -1:
                self._remove_turn()

        # Get proc
        proc = self.stack.peek()

        # If no action and action is required
        available_actions = proc.available_actions()
        if action is None and len(available_actions) > 0:
            return True

        # If action but it's available
        if action is not None:
            if len(available_actions) == 0 and action.action_type == ActionType.CONTINUE:
                # Allow no action
                action.action_type = None
            else:
                in_set = False
                for action_choice in available_actions:
                    if action.action_type == action_choice.action_type:
                        in_set = True
                        break
                if not in_set:
                    return True

        # Run proc
        proc.done = proc.step(action)

        # Remove done procs
        if proc.done:

            # Clear done procs
            while not self.stack.is_empty() and self.stack.peek().done:

                # If Half is done
                if isinstance(proc, Half):
                    if proc.half == 1:
                        self.state.half = self.stack.peek().half + 1
                        self.state.home_state.turn = 0
                        self.state.away_state.turn = 0
                    self.stack.pop()

                # If pre-game is over
                elif isinstance(self.stack.peek(), Pregame) and self.stack.peek().done:
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

            # Set turn and half in state
            if isinstance(self.stack.peek(), Turn):
                self.state.team_turn = self.stack.peek().home
                if not self.stack.peek().blitz and not self.stack.peek().quick_snap:
                    if self.state.team_turn:
                        self.state.home_state.turn += 1
                        self.report(Outcome(OutcomeType.TURN_START, team_home=True, n=self.state.home_state.turn))
                    elif not self.state.team_turn:
                        self.state.away_state.turn += 1
                        self.report(Outcome(OutcomeType.TURN_START, team_home=False, n=self.state.away_state.turn))

        # Update available actions
        self.set_available_actions()
        if len(self.available_actions) == 0:
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

    def _end_player_turn(self):
        """
        Removes all procs in the current turn - including the current turn proc.
        """
        x = 0
        for i in reversed(range(self.stack.size())):
            x += 1
            if isinstance(self.stack.items[i], PlayerAction):
                break
        for i in range(x):
            self.stack.pop()

    def _touchdown(self, proc):
        """
        Removes all procs in the current turn - including the current turn proc, and then creates procs to
        prepare for kickoff.
        """
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
