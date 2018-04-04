from bb.procedure import *


class Game:

    def __init__(self, home, away, arena, config, state=None):
        self.home = home
        self.away = away
        self.arena = arena
        self.state = state
        self.stack = Stack()
        self.reports = []
        self.config = config
        self.game_over = False

        if self.state is None:
            self.state = GameState(self)

    def init(self):
        # Postgame(self)
        Half(self, 2)
        Half(self, 1)
        Pregame(self)

    def step(self, action):
        """
        Executes one step in the game. If in Fast Mode, it executes several steps until action is required.
        :param action: Action from agent. Can be None if no action is required.
        :return: True if game requires action, False if not
        """
        # While procs are done and doesn't require new action
        done = True
        while done:

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

            # Call top of stack
            proc = self.stack.peek()
            while proc.done:
                self.stack.pop()
                if self.stack.is_empty():
                    self.game_over = True
                    return False
                proc = self.stack.peek()

            # Run proc
            done = proc.step(action)

            # Set proc done status
            proc.done = done

            # If not procs were added and it's done -> remove it
            if proc.done and proc == self.stack.peek():
                self.stack.pop()

            # If no more procs -> game is over
            if self.stack.is_empty():
                self.game_over = True
                return False

            # Stop at every step if in fast mode
            if not self.config.fast_mode:
                return False

        # Otherwise, request for user input
        return True

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