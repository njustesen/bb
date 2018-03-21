from model.player import PlayerState
import numpy as np
from model.arena import Tile
from enum import Enum
import random


class Dugout:

    def __init__(self):
        self.reserves = []
        self.kod = []
        self.casualties = []


class Field:

    def __init__(self, game):
        self.player_positions = {}
        self.ball_position = None
        self.game = game
        self.board = np.zeros(game.arena.board.shape)

    def put(self, player_id, pos):
        self.player_positions[player_id] = pos
        self.board[pos[0]][pos[1]] = player_id

    def remove(self, player_id, pos):
        del self.player_positions[player_id]
        self.board[pos[0]][pos[1]] = -1

    def move(self, player_id, pos_to):
        pos_from = self.player_positions[player_id]
        self.player_positions[player_id] = pos_to
        if pos_from is not None:
            self.board[pos_from[0]][pos_from[1]] = -1
        self.board[pos_to[0]][pos_to[1]] = player_id

    def swap(self, pos_from, pos_to):
        '''
        :param pos_from: A position on the field
        :param pos_to: A position on the field
        :return:
        '''
        player_from_id = self.board[pos_from[0]][pos_from[1]]
        if player_from_id in self.player_positions:
            self.player_positions[player_from_id] = pos_to

        player_to_id = self.board[pos_to[0]][pos_to[1]]
        if player_to_id > -1:
            self.player_positions[player_to_id] = pos_from
        self.board[pos_to[0]][pos_to[1]] = player_from_id
        self.board[pos_from[0]][pos_from[1]] = player_to_id

    def get_player_id_at(self, pos):
        if self.board[pos[0]][pos[1]] == -1:
            return None
        return self.board[pos[0]][pos[1]]

    def get_player_position(self, player_id):
        if player_id in self.player_positions:
            return self.player_positions[player_id]
        return None

    def is_setup_legal(self, home, tile=None, max=11, min=4):
        cnt = 0
        for y in range(len(self.board)):
            for x in range(len(self.board[0])):
                if not self.game.arena.is_team_side(home):
                    continue
                if tile is None or self.board[y][x] == tile:
                    player_id = self.board[y][x]
                    if player_id is not None and player_id in self.game.get_team(home).has_player_by_id(player_id):
                        cnt += 1
        if cnt > max or cnt < min:
            return False
        return True

    def is_setup_legal_scrimmage(self, home):
        if home:
            return self.is_setup_legal(home, tile=Tile.HOME_SCRIMMAGE, min=3)
        return self.is_setup_legal(home, tile=Tile.AWAY_SCRIMMAGE, min=3)

    def is_setup_legal_wings(self, home):
        if home:
            return self.is_setup_legal(home, tile=Tile.HOME_WING_LEFT, max=2, min=0) and \
                   self.is_setup_legal(home, tile=Tile.HOME_WING_RIGHT, max=2, min=0)
        return self.is_setup_legal(home, tile=Tile.AWAY_WING_LEFT, max=2, min=0) and \
               self.is_setup_legal(home, tile=Tile.AWAY_WING_RIGHT, max=2, min=0)

    def get_team_player_ids(self, home):
        if home:
            return list(set(self.player_positions.keys()) & set(self.game.home.get_player_ids()))
        return list(set(self.player_positions.keys()) & set(self.game.away.get_player_ids()))

    def get_random_player(self, home):
        return random.choice(self.get_team_player_ids(home))


class TeamState:

    def __init__(self, team):
        self.bribes = 0
        self.babes = 0
        self.apothecary_available = team.apothecary
        self.player_states = {player.id: PlayerState.READY for player in team.players}
        self.score = 0
        self.turn = 0
        self.apothecary = team.apothecary
        self.rerolls_start = team.rerolls
        self.rerolls = team.rerolls
        self.ass_coaches = team.ass_coaches
        self.cheerleaders = team.cheerleaders
        self.fame = 0


class Weather(Enum):
    SWELTERING_HEAT = 1
    VERY_SUNNY = 2
    NICE = 3
    POURING_RAIN = 4
    BLIZZARD = 5


class GameState:

    def __init__(self, game):
        self.half = 1
        self.kicking_team = None
        self.field = Field(game)
        self.home_dugout = Dugout()
        self.away_dugout = Dugout()
        self.home_state = TeamState(game.home)
        self.away_state = TeamState(game.away)
        self.weather = None
        self.gentle_gust = False

    def get_team_state(self, home):
        return self.home_state if home else self.away_state
