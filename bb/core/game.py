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
        for player_id, pos in self.state.pitch.player_positions.items():
            if self.state.pitch.board[pos.y][pos.x] != player_id:
                raise Exception(pos.to_simple() + ": " + player_id )

        for y in range(len(self.state.pitch.board)):
            for x in range(len(self.state.pitch.board[0])):
                assert self.state.pitch.board[y][x] is None or (self.state.pitch.player_positions[self.state.pitch.board[y][x]].x == x and self.state.pitch.player_positions[self.state.pitch.board[y][x]].y == y)

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

    def set_half(self, half):
        self.state.half = half

    def add_or_skip_turn(self, turns):
        '''

        :param turns 1 or -1:
        :return:
        '''
        self.state.get_team_state(True).turn += turns
        self.state.get_team_state(False).turn += turns
        if turns == -1:
            for idx in reversed(range(self.stack.size())):
                if isinstance(self.stack.items[idx], Turn):
                    home = self.stack.items[idx].home
                    self.stack.items.insert(idx, Turn(self, home=home, half=self.state.half,
                                                           turn=max(0, self.state.get_team_state(
                                                               self.home).turn - 1)))
                    self.stack.items.insert(idx, Turn(self, home=not home, half=self.state.half,
                                                           turn=max(0, self.state.get_team_state(
                                                               not self.home).turn - 1)))
                    break
        if turns == 1:
            for idx in range(self.stack.size()):
                if isinstance(self.stack.items[idx], Turn):
                    self.stack.items.pop(idx)
                    self.stack.items.pop(idx)
                    break

    def set_spectators(self, spectators):
        self.state.spectators = spectators

    def get_spectators(self):
        return self.state.spectators

    def add_bribe(self, home):
        if home:
            self.state.home_state.bribes += 1
        else:
            self.state.away_state.bribes += 1

    def use_bribe(self, home):
        if home:
            self.state.home_state.bribes -= 1
        else:
            self.state.away_state.bribes -= 1

    def get_bribes(self, home):
        return self.state.get_team_state(home).bribes

    def get_cheerleaders(self, home):
        return self.state.get_team_state(home).cheerleaders

    def get_babes(self, home):
        return self.state.get_team_state(home).babes

    def get_ass_coaches(self, home):
        return self.state.get_team_state(home).ass_coaches

    def has_masterchef(self, home):
        return self.state.get_team_state(home).masterchef

    def has_wizard_available(self, home):
        return self.state.get_team_state(home).wizard_available

    def has_apothecary_available(self, home):
        return self.state.get_team_state(home).apothecary_available

    def get_team(self, home):
        return self.home if home else self.away

    def get_player(self, player_id):
        if self.get_home_by_player_id(player_id):
            return self.home.get_player_by_id(player_id)
        return self.away.get_player_by_id(player_id)

    def get_player_at(self, pos):
        player_id = self.state.pitch.get_player_id_at(pos)
        return self.get_player(player_id) if player_id is not None else None

    def get_home_by_player_id(self, player_id):
        if self.home.has_player_by_id(player_id):
            return True
        return False

    def get_team_by_player_id(self, player_id):
        if self.home.has_player_by_id(player_id):
            return self.home
        return self.away

    def is_on_team(self, player, home):
        return self.get_home_by_player_id(player.player_id) == home

    def get_player_position(self, player):
        return self.state.pitch.get_player_position(player.player_id)

    def use_reroll(self, home):
        self.state.get_team_state(home).use_reroll()
        self.state.get_team_state(home).reroll_used = True

    def add_reroll(self, home):
        self.state.get_team_state(home).rerolls += 1

    def get_rerolls_left(self, home):
        return self.state.get_team_state(home).rerolls

    def get_fame(self, home):
        return self.state.get_team_state(home).fame

    def set_fame(self, home, fame):
        self.state.get_team_state(home).fame = fame

    def set_rerolls(self, home, rerolls):
        self.state.get_team_state(home).rerolls = rerolls

    def set_team_turn(self, home, turn):
        self.state.get_team_state(home).turn = turn

    def get_team_turns(self, home):
        return self.state.get_team_state(home).turn

    def can_use_reroll(self, home):
        return self.state.can_use_reroll(home)

    def add_score(self, home):
        self.state.get_team_state(home).score += 1

    def get_kicking_team(self, half=None):
        if half is None:
            half = self.state.half
        return self.state.kicking_team if half == 1 else not self.state.kicking_team

    def set_kicking_team(self, home):
        self.state.kicking_team = home

    def get_ball_position(self):
        return self.state.pitch.ball_position

    def has_ball(self, player):
        return self.state.pitch.has_ball(player.player_id)

    def is_ball_in_air(self):
        return self.state.pitch.ball_in_air

    def set_ball_in_air(self, in_air):
        self.state.state.pitch.ball_in_air = in_air

    def set_ball_control(self, control):
        self.state.pitch.ball_in_control = control

    def get_player_state(self, player, home):
        return self.state.get_player_state(player.player_id, home)

    def get_player_ready_state(self, player, home):
        return self.state.get_player_ready_state(player.player_id, home)

    def set_player_ready_state(self, player, home, player_ready_state):
        self.state.set_player_ready_state(player.player_id, home, player_ready_state)

    def move_ball(self, x, y):
        self.state.pitch.ball_position.x += x
        self.state.pitch.ball_position.y += y

    def move_ball_to(self, pos, in_air=False, control=True):
        self.state.pitch.move_ball_to(pos, in_air=in_air, control=control)

    def is_touchdown(self, home):
        for player in self.get_team(home).players:
            if self.arena.is_touchdown(self.get_player_position(player), home):
                return True
        return False

    def is_ball_under_control(self):
        return self.state.pitch.ball_in_control

    def is_ball_out(self):
        return self.state.pitch.is_ball_out()

    def is_out_of_bounds(self, pos):
        return self.state.pitch.is_out_of_bounds(pos)

    def get_reserves(self, home):
        return self.state.get_dugout(home).reserves

    def get_kod(self, home):
        return self.state.get_dugout(home).kod

    def get_casualties(self, home):
        return self.state.get_dugout(home).casualties

    def get_dungeon(self, home):
        return self.state.get_dugout(home).casualties

    def get_players_on_pitch(self, home, state=None):
        return [self.get_player(player_id) for player_id in self.state.pitch.get_team_player_ids(home, state=state, only_pitch=True)]

    def pitch_to_reserves(self, player, home):
        self.state.pitch.remove(player.player_id)
        self.get_reserves(home).append(player.player_id)

    def pitch_to_kod(self, player, home):
        self.state.pitch.remove(player.player_id)
        self.state.get_dugout(home).kod.append(player.player_id)
        self.state.set_player_ready_state(player.player_id, home, PlayerReadyState.KOD)

    def pitch_to_casualties(self, player, home, casualty, effect, apothecary=False):
        self.state.get_team_state(home).injure_player(player.player_id, casualty, effect)
        self.state.pitch.remove(player.player_id)
        if apothecary and effect == CasualtyEffect.NONE:
            # Apothecary puts badly hurt players in the reserves
            self.state.get_dugout(home).reserves.append(player.player_id)
        else:
            self.state.get_team_state(home).injure_player(player.player_id, casualty, effect)
            self.state.get_dugout(home).casualties.append(player.player_id)

    def pitch_to_dungeon(self, player, home):
        self.state.pitch.remove(player.player_id)
        self.state.get_dugout(home).dungeon.append(player.player_id)
        self.state.set_player_ready_state(player.player_id, home, PlayerReadyState.EJECTED)

    def move_player(self, player, pos):
        self.state.pitch.move(player.player_id, pos)

    def swap(self, pos_a, pos_b):
        self.state.pitch.swap(pos_a, pos_b)

    def get_weather(self):
        return self.state.weather

    def set_weather(self, weather):
        self.state.weather = weather

    def assists(self, home, attacker, defender, ignore_guard=False):
        return self.state.pitch.assists(home, attacker, defender, ignore_guard=ignore_guard)

    def tackle_zones(self, pos, home):
        return self.state.pitch.get_tackle_zones(pos, home=home)

    def interceptors(self, pos_from, pos_to, home):
        return [self.get_player(player_id) for player_id in self.state.pitch.interceptors(pos_from, pos_to, home)]

    def pass_distance(self, pos_from, pos_to):
        return self.state.pitch.pass_distance(pos_from, pos_to)

    def passes(self, player, pos):
        return self.state.pitch.get_passes(player, pos)

    def adjacent_squares(self, pos, manhattan=False, include_out=False, exclude_occupied=False):
        return self.state.pitch.get_adjacent_squares(pos, manhattan=manhattan, include_out=include_out, exclude_occupied=exclude_occupied)

    def adjacent_player_squares(self, pos, include_home=True, include_away=True, manhattan=False, only_blockable=False, only_foulable=False):
        return self.state.pitch.get_adjacent_player_squares(pos, include_home, include_away, manhattan, only_blockable, only_foulable)

    def push_squares(self, pos_from, pos_to):
        return self.state.pitch.get_push_squares(pos_from, pos_to)

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

