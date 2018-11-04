from bb.core.procedure import *
import json
import pickle


class Game:

    def __init__(self, game_id, teams, arena, config, ruleset, home_team=None, state=None):
        self.game_id = game_id
        self.teams = {teams.team_id: team for team in teams}
        self.home_team = teams[0] if home_team is None else home_team
        self.team_by_player_id = {}
        # Dictionary with team for players
        for team in teams:
            for player in team.players:
                self.team_by_player_id[player.player_id] = team
        # Setup oppenent teams - in two player matches this is just the other team
        self.opp_teams = {}
        for i in range(len(teams)):
            x = 0 if i+1 >= len(teams) else i+1
            self.opp_teams[teams[i].team_id] = teams[x]
        self.arena = arena
        self.stack = Stack()
        self.reports = []
        self.config = config
        self.ruleset = ruleset
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
            'teams': [team.to_simple() for team in self.teams],
            'state': self.state.to_simple(),
            'game_over': self.game_over,
            'stack': self.procs(),
            'available_actions': available_actions,
            'reports': reports,
            'squares_moved': self._squares_moved(),
            'arena': self.arena.to_simple(),
            'ruleset': self.ruleset.name
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

    def get_current_team(self):
        return self.state.current_team

    def add_or_skip_turn(self, turns):
        '''

        :param turns must be 1 or -1:
        :return:
        '''

        for team_id, team_state in self.state.team_states.items():
            team_state.turn += turns

    def is_team_side(self, pos, team):
        return self.arena.is_team_side(pos, team == self.home_team)

    def set_spectators(self, spectators):
        self.state.spectators = spectators

    def get_spectators(self):
        return self.state.spectators

    def add_bribe(self, team):
        self.state.team_states[team.team_id].bribes += 1

    def use_bribe(self, team):
        self.state.team_states[team.team_id].bribes -= 1

    def get_bribes(self, team):
        return self.state.team_states[team.team_id].bribes

    def set_bribes(self, team, bribes):
        self.state.team_states[team.team_id].bribes = bribes

    def get_cheerleaders(self, team):
        return self.state.team_states[team.team_id].cheerleaders

    def set_cheerleaders(self, team, cheerleaders):
        self.state.team_states[team.team_id].cheerleaders = cheerleaders

    def add_cheerleader(self, team):
        self.state.team_states[team.team_id].cheerleaders += 1

    def get_babes(self, team):
        return self.state.team_states[team.team_id].babes

    def set_babes(self, team, babes):
        self.state.team_states[team.team_id].babes = babes

    def add_babe(self, team):
        self.state.team_states[team.team_id].babes += 1

    def get_ass_coaches(self, team):
        return self.state.team_states[team.team_id].ass_coaches

    def add_ass_coaches(self, team):
        self.state.team_states[team.team_id].ass_coaches += 1

    def set_ass_coaches(self, team, ass_coaches):
        self.state.team_states[team.team_id].ass_coaches = ass_coaches

    def has_masterchef(self, team):
        return self.state.team_states[team.team_id].masterchef

    def set_masterchef(self, team, masterchef):
        self.state.team_states[team.team_id].masterchef = masterchef

    def has_wizard_available(self, team):
        return self.state.team_states[team.team_id].wizard_available

    def set_wizard_available(self, team, wizard):
        self.state.team_states[team.team_id].wizard_available = wizard

    def has_apothecary_available(self, team):
        return self.state.team_states[team.team_id].apothecary_available

    def set_apothecary_available(self, team, apothecary):
        self.state.team_states[team.team_id].apothecary_available = apothecary

    def get_player(self, player_id):
        return self.team_by_player_id[player_id].players_by_id[player_id]

    def get_player_at(self, pos):
        player_id = self.state.pitch.get_player_id_at(pos)
        return self.get_player(player_id) if player_id is not None else None

    def set_turn_order(self, team):
        self.state.turn_order = []
        added = False
        for team_id, t in self.teams.items():
            if added:
                self.state.turn_order.insert(0, t)
            else:
                self.state.turn_order.append(t)
            if team_id == team.team_id:
                added = True

    def get_turn_order(self):
        return self.state.turn_order

    def is_home_team(self, team):
        return team == self.home_team

    def get_opp_team(self, team):
        return self.opp_teams[team.team_id]

    def get_team_by_player(self, player):
        return self.team_by_player_id[player.player_id]

    def get_team_by_player_id(self, player_id):
        return self.team_by_player_id[player_id]

    def is_on_team(self, player, team):
        return self.team_by_player_id[player.player.player_id].team_id == team.team_id

    def get_player_position(self, player):
        return self.state.pitch.get_player_position(player.player_id)

    def use_reroll(self, team):
        self.state.team_state[team.team_id].use_reroll()

    def add_reroll(self, team):
        self.state.team_state[team.team_id].rerolls += 1

    def get_rerolls_left(self, team):
        return self.state.team_state[team.team_id].rerolls

    def get_fame(self, team):
        return self.state.team_state[team.team_id].fame

    def set_fame(self, team, fame):
        self.state.team_state[team.team_id].fame = fame

    def set_rerolls(self, team, rerolls):
        self.state.team_state[team.team_id].rerolls = rerolls

    def set_team_turn(self, team, turn):
        self.state.team_state[team.team_id].turn = turn

    def get_team_turn(self, team):
        return self.state.team_state[team.team_id].turn

    def can_use_reroll(self, team):
        return not self.state.team_state[team.team_id].reroll_used and self.state.team_state[
            team.team_id].rerolls > 0 and self.state.current_team == team

    def add_score(self, team):
        self.state.get_team_state(team).score += 1

    def get_kicking_team(self, half=None):
        if half is None:
            half = self.state.half
        return self.state.kicking_team if half == 1 else not self.state.kicking_team

    def set_kicking_team(self, team):
        self.state.kicking_team = team

    def get_receiving_team(self, half=None):
        return self.get_opp_team(self.get_kicking_team(half))

    def get_ball_position(self):
        return self.state.pitch.get_ball_position()

    def has_ball(self, player):
        ball = self.state.pitch.get_ball_at(self.get_player_position(player))
        return ball.position if ball is not None else None

    def get_player_state(self, player, team):
        return self.state.get_player_state(player.player_id, team)

    def get_player_ready_state(self, player, team):
        return self.state.get_player_ready_state(player.player_id, team)

    def set_player_ready_state(self, player, team, player_ready_state):
        self.state.set_player_ready_state(player.player_id, team, player_ready_state)

    def is_touchdown(self, team):
        for player in self.teams[team.team_id].players:
            if self.arena.is_touchdown(self.get_player_position(player), team):
                return True
        return False

    def is_out_of_bounds(self, pos):
        return self.state.pitch.is_out_of_bounds(pos)

    def get_reserves(self, team):
        return self.state.get_dugout(team).reserves

    def get_kod(self, team):
        return self.state.get_dugout(team).kod

    def get_casualties(self, team):
        return self.state.get_dugout(team).casualties

    def get_dungeon(self, team):
        return self.state.get_dugout(team).casualties

    def get_players_on_pitch(self, team, state=None):
        return [self.get_player(player_id) for player_id in self.state.pitch.get_team_player_ids(team, state=state, only_pitch=True)]

    def get_team_state(self, team):
        return self.state.team_states[team.team_id]

    def pitch_to_reserves(self, player, team):
        self.state.pitch.remove(player.player_id)
        self.get_reserves(team).append(player.player_id)

    def reserves_to_pitch(self, player, team, pos):
        self.state.get_dugout(team).reserves.remove(player)
        player_at = self.get_player_at(pos)
        if player_at is not None:
            self.pitch_to_reserves(player_at, team)
        self.state.pitch.put(player, pos)

    def pitch_to_kod(self, player, team):
        self.state.pitch.remove(player.player_id)
        self.get_kod(team).kod.append(player.player_id)
        self.set_player_ready_state(player, team, PlayerReadyState.KOD)

    def kod_to_reserves(self, player, team):
        self.set_player_ready_state(player, team, PlayerReadyState.READY)
        self.get_kod(team).remove(player)
        self.get_reserves(team).append(player)

    def pitch_to_casualties(self, player, team, casualty, effect, apothecary=False):
        self.get_team_state(team).injure_player(player.player_id, casualty, effect)
        self.state.pitch.remove(player.player_id)
        if apothecary and effect == CasualtyEffect.NONE:
            # Apothecary puts badly hurt players in the reserves
            self.get_reserves(team).append(player.player_id)
        else:
            self.get_team_state(team).injure_player(player.player_id, casualty, effect)
            self.get_casualties(team).append(player.player_id)

    def pitch_to_dungeon(self, player, team):
        self.state.pitch.remove(player.player_id)
        self.get_dungeon(team).append(player.player_id)
        self.set_player_ready_state(player, team, PlayerReadyState.EJECTED)

    def move_player(self, player, pos):
        self.state.pitch.move(player.player_id, pos)

    def swap(self, pos_a, pos_b):
        self.state.pitch.swap(pos_a, pos_b)

    def get_weather(self):
        return self.state.weather

    def set_weather(self, weather):
        self.state.weather = weather

    def assists(self, team, attacker, defender, ignore_guard=False):
        return self.state.pitch.assists(team, attacker, defender, ignore_guard=ignore_guard)

    def tackle_zones(self, pos, team):
        return self.state.pitch.get_tackle_zones(pos, team=team)

    def interceptors(self, pos_from, pos_to, team):
        return [self.get_player(player_id) for player_id in self.state.pitch.interceptors(pos_from, pos_to, team)]

    def pass_distance(self, pos_from, pos_to):
        return self.state.pitch.pass_distance(pos_from, pos_to)

    def passes(self, player, pos):
        return self.state.pitch.get_passes(player, pos)

    def adjacent_squares(self, pos, manhattan=False, include_out=False, exclude_occupied=False):
        return self.state.pitch.get_adjacent_squares(pos, manhattan=manhattan, include_out=include_out, exclude_occupied=exclude_occupied)

    def adjacent_player_squares(self, pos, include_team=True, include_away=True, manhattan=False, only_blockable=False, only_foulable=False):
        return self.state.pitch.get_adjacent_player_squares(pos, include_team, include_away, manhattan, only_blockable, only_foulable)

    def push_squares(self, pos_from, pos_to):
        return self.state.pitch.get_push_squares(pos_from, pos_to)

    def reset_turn(self, team):
        self.state.current_team = None
        self.state.team_state[team.team_id].reset_turn()

    def reset_kickoff(self):
        self.state.current_team = None
        for team_id, team_state in self.state.team_states.items():
            team_state.reset_turn()

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

