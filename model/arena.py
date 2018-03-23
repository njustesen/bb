import numpy as np
from enum import Enum


class Tile(Enum):
    NONE = 1
    HOME_TOUCHDOWN = 2
    HOME_WING_LEFT = 3
    HOME_WING_RIGHT = 4
    HOME_SCRIMMAGE = 5
    AWAY_TOUCHDOWN = 6
    AWAY_WING_LEFT = 7
    AWAY_WING_RIGHT = 8
    AWAY_SCRIMMAGE = 9
    CROWD = 10


class Arena:

    def __init__(self, name, board):
        self.name = name
        self.board = board
        self.home_tiles = [Tile.HOME, Tile.HOME_TOUCHDOWN, Tile.HOME_WING_LEFT, Tile.HOME_WING_RIGHT]
        self.away_tiles = [Tile.AWAY, Tile.AWAY_TOUCHDOWN, Tile.AWAY_WING_LEFT, Tile.AWAY_WING_RIGHT]
        self.scrimmage_tiles = [Tile.HOME_SCRIMMAGE, Tile.AWAY_SCRIMMAGE]
        self.wing_right_tiles = [Tile.HOME_WING_RIGHT, Tile.AWAY_WING_RIGHT]
        self.wing_left_tiles = [Tile.HOME_WING_LEFT, Tile.AWAY_WING_LEFT]

    def is_team_side(self, pos, home):
        if home:
            return self.board[pos[0]][pos[1]] in self.home_tiles
        return self.board[pos[0]][pos[1]] in self.away_tiles

    def is_scrimmage(self, pos):
        return self.board[pos[0]][pos[1]] in self.scrimmage_tiles

    def is_touchdown(self, pos, team):
        '''
        :param pos:
        :param team: Ture if home team and False if away team.
        :return: Whether pos is within team's touchdown zone
        '''
        return self.board[pos[0]][pos[1]] in self.scrimmage_tiles

    def is_wing(self, pos, right):
        if right:
            return self.board[pos[0]][pos[1]] in self.wing_right_tiles
        return self.board[pos[0]][pos[1]] in self.wing_left_tiles

