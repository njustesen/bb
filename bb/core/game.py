from bb.core.procedure import *
import json
import pickle


class Game:

    def __init__(self, game_id, teams, arena, config, ruleset, home_team=None, state=None):
        self.game_id = game_id
        self.teams = {teams.team_id: team for team in teams}
        self.home_team = teams[0] if home_team is None else home_team
        self.team_by_player_id = {}
        self.player_by_id = {}
        # Dictionary with team for players
        for team in teams:
            for player in team.players:
                self.team_by_player_id[player.player_id] = team
                self.player_by_id[player.player_id] = player
        # Setup oppenent teams - in two player matches this is just the other team
        self.opp_teams = {}
        for i in range(len(teams)):
            x = 0 if i+1 >= len(teams) else i+1
            self.opp_teams[teams[i].team_id] = teams[x]
        self.arena = arena
        self.config = config
        self.ruleset = ruleset
        self.game_over = False
        self.available_actions = []
        self.state = state if state is not None else GameState(self)

    def _squares_moved(self):
        for proc in self.state.stack.items:
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
        for report in self.state.reports:
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
        proc = self.state.stack.peek()

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
            while not self.state.stack.is_empty() and self.state.stack.peek().done:
                print("--Proc={}".format(self.state.stack.peek()))
                self.state.stack.pop()

            # Is game over
            if self.state.stack.is_empty():
                return False

        print("-Proc={}".format(self.state.stack.peek()))

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
        self.available_actions = self.state.stack.peek().available_actions()
        assert(self.available_actions is not None)

    def report(self, outcome):
        print(outcome.outcome_type.name)
        #print(json.dumps(outcome.to_simple()))
        self.state.reports.append(outcome)

    def remove_balls(self):
        self.state.pitch.balls.clear()

    def get_current_team(self):
        return self.state.current_team

    def is_last_turn(self):
        return self.get_next_team().state.turn == self.config.rounds and self.state.half == 2

    def is_last_round(self):
        return self.state.round == self.config.rounds

    def get_next_team(self):
        idx = self.state.turn_order.index(self.get_current_team())
        if idx+1 == len(self.state.turn_order):
            return self.state.turn_order[0]
        return self.state.turn_order[idx+1]

    def add_or_skip_turn(self, turns):
        """

        :param turns must be 1 or -1:
        :return:
        """

        for team_id, team_state in self.state.team_states.items():
            team_state.turn += turns

    def is_team_side(self, pos, team):
        return self.arena.is_team_side(pos, team == self.home_team)

    def set_spectators(self, spectators):
        self.state.spectators = spectators

    def get_spectators(self):
        return self.state.spectators

    def get_player(self, player_id):
        return self.player_by_id[player_id]

    def get_player_at(self, pos):
        player_id = self.state.pitch.get_player_id_at(pos)
        return self.player_by_id[player_id] if player_id is not None else None

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

    def get_reserves(self, team):
        return self.state.get_dugout(team).reserves

    def get_kods(self, team):
        return self.state.get_dugout(team).kod

    def get_casualties(self, team):
        return self.state.get_dugout(team).casualties

    def get_dungeon(self, team):
        return self.state.get_dugout(team).dungeon

    def can_use_reroll(self, team):
        return not team.state.reroll_used and team.state.rerolls > 0 and self.state.current_team == team

    def get_kicking_team(self, half=None):
        if half is None:
            return self.state.kicking_this_drive
        return self.state.kicking_first_half if half == 1 else not self.state.receiving_first_half

    def get_receiving_team(self, half=None):
        if half is None:
            return self.state.receiving_team_this_drive
        return self.state.receiving_team_first_half if half == 1 else not self.state.kicking_first_half

    def get_ball_position(self):
        return self.state.pitch.get_ball_position()

    def has_ball(self, player):
        ball = self.state.pitch.get_ball_at(player.position)
        return ball.position if ball is not None else None

    def get_ball_at(self, pos):
        return self.state.pitch.get_ball_at(pos)

    def is_touchdown(self, player):
        return self.arena.is_touchdown(player)

    def is_out_of_bounds(self, pos):
        return self.state.pitch.is_out_of_bounds(pos)

    def get_players_on_pitch(self, team, ready=None):
        return [player for player in team.players
                if player.position is not None and (ready is None or ready == player.state.ready)]

    def pitch_to_reserves(self, player):
        self.state.pitch.remove(player)
        self.get_reserves(player.team).append(player)
        player.state.ready = PlayerReadyState.READY

    def reserves_to_pitch(self, player, pos):
        self.get_reserves(player.team).remove(player)
        player_at = self.get_player_at(pos)
        if player_at is not None:
            self.pitch_to_reserves(player_at)
        self.state.pitch.put(player, pos)

    def pitch_to_kod(self, player):
        self.state.pitch.remove(player)
        self.get_kods(player.team).append(player)
        player.state.ready = PlayerReadyState.KOD

    def kod_to_reserves(self, player):
        player.ready = PlayerReadyState.READY
        self.get_kods(player.team).remove(player)
        self.get_reserves(player.team).append(player)

    def pitch_to_casualties(self, player, casualty, effect, apothecary=False):
        self.state.pitch.remove(player)
        if apothecary and effect == CasualtyEffect.NONE:
            # Apothecary puts badly hurt players in the reserves
            self.get_reserves(player.team).append(player)
        else:
            player.state.casualty = casualty
            player.state.casualty_effect = effect
            self.get_casualties(player.team).append(player)

    def pitch_to_dungeon(self, player):
        self.state.pitch.remove(player)
        self.get_dungeon(player.team).append(player)
        player.ready = PlayerReadyState.EJECTED

    def move_player(self, player, pos):
        self.state.pitch.move(player, pos)

    def swap(self, pos_a, pos_b):
        self.state.pitch.swap(pos_a, pos_b)

    def assists(self, player, opp_player, ignore_guard=False):
        return self.state.pitch.assists(player, opp_player, ignore_guard=ignore_guard)

    def interceptors(self, passer, pos):
        return self.state.pitch.interceptors(passer, pos)

    def pass_distance(self, passer, pos):
        return self.state.pitch.pass_distance(passer, pos)

    def passes(self, player, pos):
        return self.state.pitch.passes(player, pos)

    def adjacent_squares(self, pos, manhattan=False, include_out=False, exclude_occupied=False):
        return self.state.pitch.get_adjacent_squares(pos, manhattan=manhattan, include_out=include_out, exclude_occupied=exclude_occupied)

    def adjacent_player_squares(self, player, include_own=True, include_opp=True, manhattan=False, only_blockable=False, only_foulable=False):
        return self.state.pitch.adjacent_player_squares(player, include_own, include_opp, manhattan, only_blockable, only_foulable)

    def num_tackle_zones_in(self, player):
        return self.state.pitch.num_tackle_zones_in(player)

    def num_tackle_zones_at(self, player, position):
        return self.state.pitch.num_tackle_zones_at(player, position)

    def tackle_zones_in_detailed(self, player):
        return self.state.pitch.tackle_zones_detailed(player)

    def push_squares(self, pos_from, pos_to):
        return self.state.pitch.get_push_squares(pos_from, pos_to)

    def reset_turn(self, team):
        self.state.current_team = None
        team.reset_turn()

    def reset_kickoff(self):
        self.state.current_team = None
        for team in self.teams:
            team.reset_turn()

    def procs(self):
        procs = []
        for proc in self.state.stack.items:
            if isinstance(proc, Turn) and proc.quick_snap:
                procs.append("QuickSnap")
            elif isinstance(proc, Turn) and proc.blitz:
                procs.append("Blitz")
            else:
                procs.append(proc.__class__.__name__)
        return procs

