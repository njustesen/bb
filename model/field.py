import numpy as np
import random
from model import Tile, Skill, PlayerState, Rules, Square


class Field:

    def __init__(self, game):
        self.player_positions = {}
        self.ball_position = None
        self.ball_in_air = False
        self.game = game
        self.board = np.full(game.arena.board.shape, -1)

    def put(self, player_id, pos):
        self.player_positions[player_id] = pos
        self.board[pos.y][pos.x] = player_id

    def remove(self, player_id):
        pos = self.player_positions[player_id]
        del self.player_positions[player_id]
        self.board[pos.y][pos.x] = -1

    def move(self, player_id, pos_to):
        pos_from = self.player_positions[player_id]
        if self.board[pos_to.y][pos_to.x] != -1:
            raise Exception("Player cannot be moved on top of another player")
        self.board[pos_from.y][pos_from.x] = -1
        self.board[pos_to.y][pos_to.x] = player_id
        self.player_positions[player_id] = pos_to

    def swap(self, pos_from, pos_to):
        """
        :param pos_from: A position on the field
        :param pos_to: A position on the field
        :return:
        """
        player_from_id = self.board[pos_from.y][pos_from.x]
        if player_from_id in self.player_positions:
            self.player_positions[player_from_id] = pos_to

        player_to_id = self.board[pos_to.y][pos_to.x]
        if player_to_id > -1:
            self.player_positions[player_to_id] = pos_from
        self.board[pos_to.y][pos_to.x] = player_from_id
        self.board[pos_from.y][pos_from.x] = player_to_id

    def has_ball(self, player_id):
        if not self.ball_in_air:
            return self.ball_position is not None and self.ball_position == self.get_player_position(player_id)

    def get_player_id_at(self, pos):
        if pos.y < 0 or pos.y >= len(self.board.y) or pos.x < 0 or pos.x >= len(self.board):
            raise Exception("Position is out of the board")
        if self.board[pos.y][pos.x] == -1:
            return None
        return self.board[pos.y][pos.x]

    def get_player_position(self, player_id):
        if player_id in self.player_positions:
            return self.player_positions[player_id]
        return None

    def is_setup_legal(self, home, tile=None, max_players=11, min_players=4):
        cnt = 0
        for y in range(len(self.board)):
            for x in range(len(self.board[0])):
                if not self.game.arena.is_team_side(home):
                    continue
                if tile is None or self.board[y][x] == tile:
                    player_id = self.board[y][x]
                    if player_id is not None and player_id in self.game.get_team(home).has_player_by_id(player_id):
                        cnt += 1
        if cnt > max_players or cnt < min_players:
            return False
        return True

    def is_setup_legal_scrimmage(self, home):
        if home:
            return self.is_setup_legal(home, tile=Tile.HOME_SCRIMMAGE, min_players=3)
        return self.is_setup_legal(home, tile=Tile.AWAY_SCRIMMAGE, min_players=3)

    def is_setup_legal_wings(self, home):
        if home:
            return self.is_setup_legal(home, tile=Tile.HOME_WING_LEFT, max_players=2, min_players=0) and \
                   self.is_setup_legal(home, tile=Tile.HOME_WING_RIGHT, max_players=2, min_players=0)
        return self.is_setup_legal(home, tile=Tile.AWAY_WING_LEFT, max_players=2, min_players=0) and \
               self.is_setup_legal(home, tile=Tile.AWAY_WING_RIGHT, max_players=2, min_players=0)

    def get_team_player_ids(self, home):
        if home:
            return list(set(self.player_positions.keys()) & set(self.game.home.get_player_ids()))
        return list(set(self.player_positions.keys()) & set(self.game.away.get_player_ids()))

    def get_random_player(self, home):
        return random.choice(self.get_team_player_ids(home))

    def is_ball_at(self, pos, in_air=False):
        return self.ball_position == pos and not self.ball_in_air

    def move_ball(self, pos, in_air=False):
        self.ball_position = pos
        self.ball_in_air = in_air

    def is_ball_out(self):
        return self.is_out_of_bounds(self.ball_position)

    def is_out_of_bounds(self, pos):
        return not (pos.x < 0 or pos.x >= len(self.board[0]) or pos.y < 0 or pos.y >= len(self.board))

    def has_tackle_zone(self, player):
        if Rules.has_tackle_zone[self.game.state.get_player_state(player.player_id)]:
            return False
        if player.has_skill(Skill.TITCHY):
            return False
        return True

    def get_push_squares(self, pos_from, pos_to):
        squares_to = self.game.field.get_adjacent_squares(pos_to, include_out=True)
        squares_empty = []
        squares_out = []
        squares = []
        for square in squares_to:
            if pos_from.distance(square, manhattan=True) >= 3:
                if self.game.state.field.get_player_id_at(square) is None:
                    squares_empty.append(square)
                if self.game.state.field.is_out_of_bounds(square):
                    squares_out.append(square)
                squares.append(square)
        if len(squares_empty) > 0:
            return squares_empty
        if len(squares_out) > 0:
            return squares_out
        return squares

    def get_adjacent_squares(self, pos, manhattan=False, include_out=False):
        squares = []
        for yy in range(-1, 0, 1):
            for xx in range(-1, 0, 1):
                if yy == 0 and xx == 0:
                    continue
                sq = Square(xx, yy)
                if not include_out and self.is_out_of_bounds(sq):
                    continue
                if not manhattan:
                    squares.append(sq)
                else:
                    if xx == 0 or yy == 0:
                        squares.append(sq)
        return squares

    def get_adjacent_player_squares(self, pos, home=True, away=True, manhattan=False):
        squares = []
        for square in self.get_adjacent_squares(pos, manhattan=manhattan):
            player_id = self.get_player_id_at(square)
            team_home = self.game.get_home_by_player_id(player_id)
            if team_home and home or not team_home and away:
                squares.append(squares)
        return squares

    def get_tackle_zones(self, pos):
        tackle_zones = 0
        own_player_id = self.get_player_id_at(pos)
        own_team_home = self.game.get_team_by_player_id(own_player_id)
        for square in self.get_adjacent_player_squares(pos, home=not own_team_home, away=own_team_home):
            player_id = self.get_player_id_at(square)
            player = self.game.get_player(player_id)
            if player_id is not None and self.has_tackle_zone(player):
                tackle_zones += 1
        return tackle_zones

    def get_tackle_zones_detailed(self, pos):
        tackle_zones = 0
        tackle_id = None
        prehensile_tail_id = None
        diving_tackle_id = None
        shadowing_id = None
        tentacles_id = None
        own_player_id = self.get_player_id_at(pos)
        own_team_home = self.game.get_team_by_player_id(own_player_id)
        for square in self.get_adjacent_player_squares(pos, home=not own_team_home, away=own_team_home):
            player_id = self.get_player_id_at(square)
            player = self.game.get_player(player_id)
            if player_id is not None and self.has_tackle_zone(player):
                tackle_zones += 1
            if tackle_id is None and player.has_skill(Skill.TACKLE):
                tackle_id = player_id
            if prehensile_tail_id is None and player.has_skill(Skill.PREHENSILE_TAIL):
                prehensile_tail_id = player_id
            if diving_tackle_id is None and player.has_skill(Skill.DIVING_TACKLE):
                diving_tackle_id = player_id
            if shadowing_id is None and player.has_skill(Skill.SHADOWING):
                diving_tackle_id = player_id
            if tentacles_id is None and player.has_skill(Skill.TENTACLES):
                tentacles_id = player_id

        return tackle_zones, tackle_id, prehensile_tail_id, diving_tackle_id, shadowing_id, tentacles_id

    def assists(self, home, player_from, player_to):
        pos_from = self.get_player_position(player_from.player_id)
        pos_to = self.get_player_position(player_to.player_id)
        assists = []
        for yy in range(-1, 0, 1):
            for xx in range(-1, 0, 1):
                if yy == 0 and xx == 0:
                    continue
                p = [pos_to.y+xx, pos_to.x+yy]
                if not self.is_out_of_bounds(p) and not np.array_equal(pos_from, p):
                    player_id = self.get_player_id_at(p)
                    if player_id is not None:
                        if player_id in self.game.get_home_by_player_id(player_id) != home:
                            if self.game.state.get_player_state(player_id) == PlayerState.BONE_HEADED:
                                continue
                            if self.game.get_player(player_id).has_skill(Skill.GUARD) or \
                                            self.get_tackle_zones(player_id) <= 1:
                                assists.append(player_id)
        return assists