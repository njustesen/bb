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

    def init(self):
        # Postgame(self)
        Half(self, 2)
        Half(self, 1)
        Pregame(self)
        self.set_available_actions()

    def step(self, action):
        """
        Executes one step in the game. If in Fast Mode, it executes several steps until action is required.
        :param action: Action from agent. Can be None if no action is required.
        :return: True if game requires action, False if not
        """

        # If touchdown, end turn and add kickoff
        if isinstance(self.stack.peek(), Touchdown):
            self._touchdown(self.stack.peek())

        # If turnover, end turn
        if isinstance(self.stack.peek(), Turnover):
            self._end_turn()

        # If riot -> remove one turn
        if isinstance(self.stack.peek(), Riot):
            if self.stack.peek().effect == 1:
                self._add_turn()
            elif self.stack.peek().effect == -1:
                self._remove_turn()

        # Run proc
        proc = self.stack.peek()
        proc.done = proc.step(action)

        # Remove done procs
        proc = self.stack.peek()
        while proc.done:
            self.stack.pop()
            if self.stack.is_empty():
                self.game_over = True
                return False
            proc = self.stack.peek()

        # Otherwise, request for user input
        self.set_available_actions()
        return True

    def set_available_actions(self):
        self.available_actions = self.stack.peek().available_actions()

    def report(self, outcome):
        self.reports.append(outcome)

    def _remove_turn(self):
        for idx in range(self.stack.size()):
            if isinstance(self.stack.items[idx], Turn):
                self.stack.items.remove(idx)
                self.stack.items.remove(idx)
                break

    def _add_turn(self):
        home = False
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
        self._end_turn()
        KickOff(self, proc.home)
        Setup(self, not proc.home)
        Setup(self, proc.home)
        ClearBoard(self)

    def get_team(self, home):
        return self.home if home else self.away

    def get_player(self, player_id):
        home = self.home.get_player_by_id(player_id)
        if home is not None:
            return home
        away = self.away.get_player_by_id(player_id)
        return away

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
            procs.append(proc.__class__.__name__)
        return procs

    def to_simple(self):
        available_actions = []
        for action in self.available_actions:
            available_actions.append(action.to_simple())
        return {
            'game_id': self.game_id,
            'home_team': self.home.to_simple(),
            'away_team': self.away.to_simple(),
            'state': self.state.to_simple(),
            'game_over': self.game_over,
            'stack': self.procs(),
            'available_actions': available_actions
        }