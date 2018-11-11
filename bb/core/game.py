from bb.core.procedure import *
import json
import pickle


class Game:

    def __init__(self, game_id, teams, arena, config, ruleset, state=None):
        self.game_id = game_id
        assert len(teams) == 2
        self.teams = teams
        self.team_by_id = {team.team_id: team for team in teams}
        self.home_team = teams[0]
        self.away_team = teams[1]
        self.team_by_player_id = {}
        self.player_by_id = {}
        # Dictionary with team for players
        for team in teams:
            for player in team.players:
                self.team_by_player_id[player.player_id] = team
                self.player_by_id[player.player_id] = player
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
            'home_team': self.home_team.to_simple(),
            'away_team': self.away_team.to_simple(),
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
                if len(action_choice.players) > 0 and self.get_player(action.player_from_id) not in action_choice.players:
                    print("Illegal player_id")
                    return False
                if len(action_choice.positions) > 0 and action.pos_to not in action_choice.positions:
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

        # Clear done procs
        while not self.state.stack.is_empty() and self.state.stack.peek().done:
            print("--Proc={}".format(self.state.stack.peek()))
            self.state.stack.pop()

        # Is game over
        if self.state.stack.is_empty():
            return False

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
        for y in range(len(self.state.pitch.board)):
            for x in range(len(self.state.pitch.board)):
                assert self.state.pitch.board[y][x] is None or \
                    (self.state.pitch.board[y][x].position.x == x and self.state.pitch.board[y][x].position.y == y)

        for team in self.teams:
            for player in team.players:
                assert player.position is None or self.state.pitch.board[player.position.y][player.position.x] == player

        # Remove all finished procs
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
            self.step(Action(ActionType.END_PLAYER_TURN, player_from_id=self.available_actions[0].players[0].player_id))
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

    def is_team_side(self, pos, team):
        if team == self.home_team:
            return self.arena.board[pos.y][pos.x] in TwoPlayerArena.home_tiles
        return self.arena.board[pos.y][pos.x] in TwoPlayerArena.away_tiles

    def get_team_side(self, team):
        tiles = []
        for y in range(len(self.arena.board)):
            for x in range(len(self.arena.board[y])):
                if self.arena.board[y][x] in (TwoPlayerArena.home_tiles if team == self.home_team else TwoPlayerArena.away_tiles):
                    tiles.append(Square(x, y))
        return tiles

    def is_scrimmage(self, pos):
        return self.arena.board[pos.y][pos.x] in TwoPlayerArena.scrimmage_tiles

    def is_touchdown(self, player):
        if player.team == self.home_team:
            return self.arena.board[player.position.y][player.position.x] == Tile.AWAY_TOUCHDOWN
        return self.arena.board[player.position.y][player.position.x] == Tile.HOME_TOUCHDOWN

    def is_wing(self, pos, right):
        if right:
            return self.arena.board[pos.y][pos.x] in TwoPlayerArena.wing_right_tiles
        return self.arena.board[pos.y][pos.x] in TwoPlayerArena.wing_left_tiles

    def remove_balls(self):
        self.state.pitch.balls.clear()

    def is_last_turn(self):
        return self.get_next_team().state.turn == self.config.rounds and self.state.half == 2

    def is_last_round(self):
        return self.state.round == self.config.rounds

    def get_next_team(self):
        idx = self.state.turn_order.index(self.state.current_team)
        if idx+1 == len(self.state.turn_order):
            return self.state.turn_order[0]
        return self.state.turn_order[idx+1]

    def add_or_skip_turn(self, turns):
        for team in self.teams:
            team.state.turn += turns
            assert team.state.turn >= 0

    def get_player(self, player_id):
        return self.player_by_id[player_id]

    def get_player_at(self, pos):
        return self.state.pitch.board[pos.y][pos.x]

    def set_turn_order_from(self, first_team):
        before = []
        after = []
        added = False
        if len(self.state.turn_order) == 0:
            self.state.turn_order = [team for team in self.teams]
        for team in self.get_turn_order():
            if team == first_team:
                added = True
            if not added:
                before.append(team)
            else:
                after.append(team)
        self.state.turn_order = after + before

    def set_turn_order_after(self, last_team):
        before = []
        after = []
        added = False
        if len(self.state.turn_order) == 0:
            self.state.turn_order = [team for team in self.teams]
        for team in self.get_turn_order():
            if not added:
                before.append(team)
            else:
                after.append(team)
            if team == last_team:
                added = True
        self.state.turn_order = after + before

    def get_turn_order(self):
        return self.state.turn_order

    def is_home_team(self, team):
        return team == self.home_team

    def get_opp_team(self, team):
        return self.home_team if self.away_team == team else self.away_team

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
        return self.state.kicking_first_half if half == 1 else self.state.receiving_first_half

    def get_receiving_team(self, half=None):
        if half is None:
            return self.state.receiving_this_drive
        return self.state.receiving_first_half if half == 1 else self.state.kicking_first_half

    def get_ball_position(self):
        return self.state.pitch.get_ball_position()

    def has_ball(self, player):
        ball = self.state.pitch.get_ball_at(player.position)
        return True if ball is not None and ball.is_carried else False

    def get_ball_at(self, pos):
        return self.state.pitch.get_ball_at(pos)

    def is_touchdown(self, player):
        return self.arena.in_opp_endzone(player.position, player.team == self.home_team)

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
        player.state.ready = PlayerReadyState.READY
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

    def swap(self, piece_a, piece_b):
        self.state.pitch.swap(piece_a, piece_b)

    def assists(self, player, opp_player, ignore_guard=False):
        return self.state.pitch.assists(player, opp_player, ignore_guard=ignore_guard)

    def interceptors(self, passer, pos):
        return self.state.pitch.interceptors(passer, pos)

    def pass_distance(self, passer, pos):
        return self.state.pitch.pass_distance(passer, pos)

    def passes(self, passer):
        return self.state.pitch.passes(passer, self.state.weather)

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

    def is_setup_legal(self, team, tile=None, max_players=11, min_players=3):
        cnt = 0
        for y in range(len(self.state.pitch.board)):
            for x in range(len(self.state.pitch.board[y])):
                if not self.is_team_side(Square(x, y), team):
                    continue
                if tile is None or self.arena.board[y][x] == tile:
                    piece = self.state.pitch.board[y][x]
                    if isinstance(piece, Player) and piece.team == team:
                        cnt += 1
        if cnt > max_players or cnt < min_players:
            return False
        return True

    def get_winner(self):
        if self.home_team.state.score > self.away_team.state.score:
            return self.home_team
        elif self.home_team.state.score < self.away_team.state.score:
            return self.away_team
        return None

    def is_setup_legal_scrimmage(self, team, min_players=3):
        if team == self.home_team:
            return self.is_setup_legal(team, tile=Tile.HOME_SCRIMMAGE, min_players=min_players)
        return self.is_setup_legal(team, tile=Tile.AWAY_SCRIMMAGE, min_players=min_players)

    def is_setup_legal_wings(self, team, min_players=0, max_players=2):
        if team == self.home_team:
            return self.is_setup_legal(team, tile=Tile.HOME_WING_LEFT, max_players=max_players, min_players=min_players) and \
                   self.is_setup_legal(team, tile=Tile.HOME_WING_RIGHT, max_players=max_players, min_players=min_players)
        return self.is_setup_legal(team, tile=Tile.AWAY_WING_LEFT, max_players=max_players, min_players=min_players) and \
               self.is_setup_legal(team, tile=Tile.AWAY_WING_RIGHT, max_players=max_players, min_players=min_players)

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

    def remove_recursive_refs(self):
        for team in self.teams:
            for player in team.players:
                player.team = None

    def add_recursive_refs(self):
        for team in self.teams:
            for player in team.players:
                player.team = team
