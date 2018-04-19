from abc import ABC, abstractmethod
import numpy as np
import random
from math import sqrt
from bb.core.util import *
from bb.core.table import *
from bb.core.exception import *


class Configuration:

    def __init__(self):
        self.fast_mode = False
        self.name = "Default"
        self.arena = None
        self.ruleset = None
        self.roster_size = 16
        self.on_field = 11
        self.scrimmage_max = 3
        self.wings_max = 2
        self.turns = 8
        self.kick_off_table = True
        self.fast_mode = False


class TeamState:

    def __init__(self, team):
        self.bribes = 0
        self.babes = 0
        self.apothecary_available = team.apothecary
        self.wizard_available = False
        self.player_states = {player.player_id: PlayerState.READY for player in team.players}
        self.injuries = {}
        self.score = 0
        self.turn = 0
        self.rerolls_start = team.rerolls
        self.rerolls = team.rerolls
        self.ass_coaches = team.ass_coaches
        self.cheerleaders = team.cheerleaders
        self.fame = 0
        self.reroll_used = False

    def to_simple(self):
        player_states = {}
        for player_id in self.player_states.keys():
            player_states[player_id] = self.player_states[player_id].name
        return {
            'bribes': self.bribes,
            'babes': self.babes,
            'apothecary_available': self.apothecary_available,
            'player_states': player_states,
            'injuries': self.injuries,
            'score': self.score,
            'turn': self.turn,
            'rerolls_start': self.rerolls_start,
            'rerolls': self.rerolls,
            'ass_coaches': self.ass_coaches,
            'cheerleaders': self.cheerleaders,
            'fame': self.fame,
            'reroll_used': self.reroll_used
        }

    def reset_half(self):
        self.reroll_used = False
        self.rerolls = self.rerolls_start
        self.turn = 0

    def reset_turn(self):
        self.reroll_used = False

    def use_reroll(self):
        self.rerolls -= 1
        self.reroll_used = True


class GameState:

    def __init__(self, game):
        self.half = 1
        self.kicking_team = None
        self.field = Field(game)
        self.home_dugout = Dugout()
        self.away_dugout = Dugout()
        self.home_state = TeamState(game.home)
        self.away_state = TeamState(game.away)
        self.weather = WeatherType.NICE
        self.gentle_gust = False
        self.team_turn = None

    def to_simple(self):
        return {
            'half': self.half,
            'kicking_team': self.kicking_team,
            'field': self.field.to_simple(),
            'home_dugout': self.home_dugout.to_simple(),
            'away_dugout': self.away_dugout.to_simple(),
            'home_state': self.home_state.to_simple(),
            'away_state': self.away_state.to_simple(),
            'weather': self.weather.name,
            'gentle_gust': self.gentle_gust,
            'team_turn': self.team_turn
        }

    def reset_turn(self, home):
        self.team_turn = None
        self.get_team_state(home).reset_turn()

    def reset_kickoff(self):
        self.team_turn = None
        self.home_state.reset_turn()
        self.away_state.reset_turn()

    def reset_half(self, home):
        self.team_turn = None
        self.get_team_state(home).reset_half()

    def get_player_state(self, player_id, home):
        return self.get_team_state(home).player_states[player_id]

    def set_player_state(self, player_id, home, player_state):
        self.get_team_state(home).player_states[player_id] = player_state

    def get_team_state(self, home):
        return self.home_state if home else self.away_state

    def get_dugout(self, home):
        return self.home_dugout if home else self.away_dugout

    def knock_out(self, home, player_id):
        self.get_team_state(home).player_states[player_id] = PlayerState.KOD
        self.field.remove(player_id)
        self.get_dugout(home).kod.append(player_id)

    def badly_hurt(self, home, player_id):
        self.get_team_state(home).player_states[player_id] = PlayerState.BH
        self.field.remove(player_id)
        self.get_dugout(home).casualties.append(player_id)

    def can_use_reroll(self, home):
        return not self.get_team_state(home).reroll_used and self.get_team_state(home).rerolls > 0 and self.team_turn == home

    def use_reroll(self, home):
        self.get_team_state(home).reroll_used = True
        self.get_team_state(home).rerolls -= 1


class Field:

    def __init__(self, game):
        self.player_positions = {}
        self.ball_position = None
        self.ball_in_air = False
        self.game = game
        self.board = []
        for y in range(len(game.arena.board)):
            row = []
            for x in range(len(game.arena.board[y])):
                row.append(None)
            self.board.append(row)

    def to_simple(self):
        ball = None
        if self.ball_position is not None:
            ball = self.ball_position.to_simple()
        board = self.board
        return {
            'ball_position': ball,
            'ball_in_air': self.ball_in_air,
            'board': board
        }

    def put(self, player_id, pos):
        self.player_positions[player_id] = pos
        self.board[pos.y][pos.x] = player_id

    def remove(self, player_id):
        pos = self.player_positions[player_id]
        del self.player_positions[player_id]
        self.board[pos.y][pos.x] = None

    def move(self, player_id, pos_to):
        pos_from = self.player_positions[player_id]
        if self.has_ball(player_id):
            self.ball_position = pos_to
        if self.board[pos_to.y][pos_to.x] is not None:
            raise Exception("Player cannot be moved on top of another player")
        self.board[pos_from.y][pos_from.x] = None
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
        if player_to_id is not None:
            self.player_positions[player_to_id] = pos_from
        self.board[pos_to.y][pos_to.x] = player_from_id
        self.board[pos_from.y][pos_from.x] = player_to_id

    def has_ball(self, player_id):
        if not self.ball_in_air:
            return self.ball_position is not None and self.ball_position == self.get_player_position(player_id)

    def get_player_id_at(self, pos):
        if pos.y < 0 or pos.y >= len(self.board[0]) or pos.x < 0 or pos.x >= len(self.board[0]):
            raise Exception("Position is out of the board")
        if self.board[pos.y][pos.x] is None:
            return None
        return self.board[pos.y][pos.x]

    def get_player_position(self, player_id):
        if player_id in self.player_positions:
            return self.player_positions[player_id]
        return None

    def is_setup_legal(self, home, tile=None, max_players=11, min_players=3):
        cnt = 0
        for y in range(len(self.board)):
            for x in range(len(self.board[y])):
                if not self.game.arena.is_team_side(Square(x, y), home):
                    continue
                if tile is None or self.game.arena.board[y][x] == tile:
                    player_id = self.board[y][x]
                    if self.game.get_team(home).has_player_by_id(player_id):
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
            include = False
            if pos_from.x == pos_to.x or pos_from.y == pos_to.y:
                if pos_from.distance(square, manhattan=False) >= 2:
                    include = True
            else:
                if pos_from.distance(square, manhattan=False) >= 3:
                    include = True
            if include:
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

    def assists(self, home, player_from, player_to, ignore_guard=False):
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
                            if (not ignore_guard and self.game.get_player(player_id).has_skill(Skill.GUARD)) or \
                                            self.get_tackle_zones(player_id) <= 1:
                                assists.append(player_id)
        return assists

    def pass_distance(self, pos_from, pos_to):
        distance = pos_from.distance(pos_to, flight=True)
        if distance <= 3.5:
            return PassDistance.QUICK_PASS
        if distance <= 6.5:
            return PassDistance.SHORT_PASS
        if distance <= 10.5:
            return PassDistance.LONG_PASS
        if distance <= 13.5:
            return PassDistance.LONG_BOMB
        return PassDistance.HAIL_MARY

    def interceptors(self, pos_from, pos_to, home):
        """
        1) Find line x from a to b
        2) Find squares s where x intersects
        3) Find manhattan neighboring n squares of s
        4) Remove squares where distance to a is larger than dist(a,b)
        5) Remove squares without standing opponents with hands
        6) Determine players on squares
        """

        # 1) Find line x from a to b
        x = get_line((pos_from.x, pos_from.y), (pos_to.x, pos_to.y))

        # 2) Find squares s where x intersects
        s = []
        for i in x:
            s.append(Square(i[0], i[1]))

        # 3) Include manhattan neighbors s into n
        # 4) Remove squares where distance to a is larger than dist(a,b)
        max_distance = pos_from.distance(pos_to)
        n = set()
        for square in s:
            n.add(square)
            for neighbor in self.get_adjacent_squares(square):

                # 4) Remove squares where distance to a is larger than dist(a,b)
                if neighbor.distance(pos_from) > max_distance:
                    continue
                if neighbor.distance(pos_to) > max_distance:
                    continue

                # 5) Remove squares without standing opponents with hands
                player_at = self.get_player_id_at(neighbor)
                if player_at is None:
                    continue
                if self.game.get_home_by_player_id(player_at) != home:
                    continue
                if self.game.state.get_player_state(player_at) not in Rules.ready_to_catch:
                    continue
                if self.game.get_player(player_at).has_skill(Skill.NO_HANDS):
                    continue

                n.add(neighbor)

        n.remove(pos_from)
        n.remove(pos_to)

        players = []
        for square in n:
            players.append(self.get_player_id_at(square))

        return players


class ActionChoice:

    def __init__(self, action_type, team, positions=[], player_ids=[]):
        self.action_type = action_type
        self.positions = positions
        self.player_ids = player_ids
        self.team = team

    def to_simple(self):
        return {
            'action_type': self.action_type.name,
            'positions': [position.to_simple() if position is not None else None for position in self.positions],
            'player_ids': self.player_ids,
            'team': self.team
        }


class Action:

    def __init__(self, action_type, pos_from=None, pos_to=None, player_from_id=None, player_to_id=None, idx=0,
                 team_home=True):
        self.action_type = action_type
        self.pos_from = pos_from
        self.pos_to = pos_to
        self.player_from_id = player_from_id
        self.player_to_id = player_to_id
        self.idx = idx
        self.home = team_home

    def to_simple(self):
        return {
            'action_type': self.action_type.name,
            'position': self.pos_from.to_simple() if self.pos_from is not None else None
        }


class Arena:

    home_tiles = [Tile.HOME, Tile.HOME_TOUCHDOWN, Tile.HOME_WING_LEFT, Tile.HOME_WING_RIGHT, Tile.HOME_SCRIMMAGE]
    away_tiles = [Tile.AWAY, Tile.AWAY_TOUCHDOWN, Tile.AWAY_WING_LEFT, Tile.AWAY_WING_RIGHT, Tile.AWAY_SCRIMMAGE]
    scrimmage_tiles = [Tile.HOME_SCRIMMAGE, Tile.AWAY_SCRIMMAGE]
    wing_right_tiles = [Tile.HOME_WING_RIGHT, Tile.AWAY_WING_RIGHT]
    wing_left_tiles = [Tile.HOME_WING_LEFT, Tile.AWAY_WING_LEFT]

    def __init__(self, board):
        self.board = board

    def is_team_side(self, pos, home):
        if home:
            return self.board[pos.y][pos.x] in Arena.home_tiles
        return self.board[pos.y][pos.x] in Arena.away_tiles

    def get_team_side(self, home):
        tiles = []
        for y in range(len(self.board)):
            for x in range(len(self.board[y])):
                if self.board[y][x] in (Arena.home_tiles if home else Arena.away_tiles):
                    tiles.append(Square(x, y))
        return tiles

    def is_scrimmage(self, pos):
        return self.board[pos.y][pos.x] in Arena.scrimmage_tiles

    def is_touchdown(self, pos, team):
        """
        :param pos:
        :param team: True if home team and False if away team.
        :return: Whether pos is within team's touchdown zone (such that they would score)
        """
        if self.is_team_side(pos, not team):
            return self.board[pos.y][pos.x] in Arena.scrimmage_tiles
        return False

    def is_wing(self, pos, right):
        if right:
            return self.board[pos.y][pos.x] in Arena.wing_right_tiles
        return self.board[pos.y][pos.x] in Arena.wing_left_tiles


class Die(ABC):

    @abstractmethod
    def get_value(self):
        pass


class DiceRoll:

    def __init__(self, dice, target=None, modifiers=None):
        self.dice = dice
        self.sum = -1
        self.target = target
        self.modifiers = modifiers

    def to_simple(self):
        dice = []
        for die in self.dice:
            dice.append(die.to_simple())
        return {
            'dice': dice,
            'sum': self.sum,
            'target': self.target,
            'modifiers': self.modifiers
        }

    def contains(self, value):
        for die in self.dice:
            if die.get_value() == value:
                return True
        return False

    def get_values(self):
        return [d.get_value for d in self.dice]

    def get_sum(self):
        if self.sum >= 0:
            return self.sum
        s = 0
        for d in self.dice:
            assert not isinstance(d, BBDie)
            s += d.get_value()
        return s

    def same(self):
        value = None
        for die in self.dice:
            if value is None or die.get_value() == value:
                value = die.get_value()
                continue
            return False
        return True


class D3(Die):

    def __init__(self):
        self.value = random.randint(1, 3)

    def get_value(self):
        return self.value

    def to_simple(self):
        return {
            'die_type': 'D3',
            'result': self.value
        }


class D6(Die):

    def __init__(self):
        self.value = random.randint(1, 6)

    def get_value(self):
        return self.value

    def to_simple(self):
        return {
            'die_type': 'D6',
            'result': self.value
        }


class D8(Die):

    def __init__(self):
        self.value = random.randint(1, 8)

    def get_value(self):
        return self.value

    def to_simple(self):
        return {
            'die_type': 'D8',
            'result': self.value
        }


class BBDie(Die):

    def __init__(self):
        r = random.randint(1, 6)
        if r == 6:
            r = 3
        self.value = BBDieResult(r)

    def get_value(self):
        return self.value

    def to_simple(self):
        return {
            'die_type': 'BB',
            'result': self.value.name
        }


class Dugout:

    def __init__(self):
        self.reserves = []
        self.kod = []
        self.casualties = []
        self.dungeon = []  # Ejected

    def to_simple(self):
        return {
            'reserves': self.reserves,
            'kod': self.kod,
            'casualties': self.casualties,
            'dungeon': self.dungeon
        }


class Position:

    def __init__(self, name, races, ma, st, ag, av, skills, cost, feeder, n_skill_sets=[], d_skill_sets=[], star_player=False):
        self.name = name
        self.races = races
        self.ma = ma
        self.st = st
        self.ag = ag
        self.av = av
        self.skills = skills
        self.cost = cost
        self.feeder = feeder
        self.n_skill_sets = n_skill_sets
        self.d_skill_sets = d_skill_sets
        self.star_player = star_player


class Player:

    def __init__(self, player_id, position, name, nr, extra_skills=[], extra_ma=0, extra_st=0, extra_ag=0, extra_av=0, niggling=0, mng=False, spp=0):
        self.player_id = player_id
        self.position = position
        self.name = name
        self.nr = nr
        self.extra_skills = extra_skills
        self.extra_ma = extra_ma
        self.extra_st = extra_st
        self.extra_ag = extra_ag
        self.extra_av = extra_av
        self.niggling = niggling
        self.mng = mng
        self.spp = spp

    def get_ag(self):
        return self.position.ag + self.extra_ag

    def get_st(self):
        return self.position.st + self.extra_st

    def get_ma(self):
        return self.position.ma + self.extra_ma

    def get_av(self):
        return self.position.av + self.extra_av

    def has_skill(self, skill):
        return skill in self.extra_skills or skill in self.position.skills

    def to_simple(self):
        skills = []
        for skill in self.extra_skills + self.position.skills:
            skills.append(skill.name)
        return {
            'player_id': self.player_id,
            'name': self.name,
            'position_name': self.position.name,
            'nr': self.nr,
            'skills': skills,
            'ma': self.get_ma(),
            'st': self.get_st(),
            'ag': self.get_ag(),
            'av': self.get_av(),
            'niggling': self.niggling,
            'mng': self.mng,
            'spp': self.spp
        }


class Square:

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def to_simple(self):
        return {
            'x': self.x,
            'y': self.y
        }

    def __eq__(self, other):
        if other is None or self is None:
            return False
        return self.x == other.x and self.y == other.x

    def distance(self, other, manhattan=False, flight=False):
        if manhattan:
            return abs(other.x - self.x) + abs(other.y - self.y)
        elif flight:
            return sqrt((other.x - self.x)**2 + (other.y - self.y)**2)
        else:
            return max(abs(other.x - self.x), abs(other.y - self.y))

    def is_adjacent(self, other, manhattan=False):
        return self.distance(other, manhattan) == 1


class Coach:

    def __init__(self, coach_id, name):
        self.coach_id = coach_id
        self.name = name

    def to_simple(self):
        return {
            'coach_id': self.coach_id,
            'name': self.name
        }


class Race:

    def __init__(self, name, positions, reroll_cost, apothecary, stakes):
        self.name = name
        self.positions = positions
        self.reroll_cost = reroll_cost
        self.apothecary = apothecary
        self.stakes = stakes


class Team:

    def __init__(self, team_id, name, race, coach, players=[], treasury=0, apothecary=False, rerolls=0, ass_coaches=0,
                 cheerleaders=0):
        self.team_id = team_id
        self.name = name
        self.coach = coach
        self.race = race
        self.players = players
        self.treasury = treasury
        self.apothecary = apothecary
        self.rerolls = rerolls
        self.ass_coaches = ass_coaches
        self.cheerleaders = cheerleaders

        self.players_by_id = {}
        for player in self.players:
            self.players_by_id[player.player_id] = player

        self.player_ids = [player.player_id for player in self.players]

    def to_simple(self):
        players = []
        players_by_id = {}
        for player in self.players:
            players.append(player.to_simple())
            players_by_id[player.player_id] = player.to_simple()
        return {
            'team_id': self.team_id,
            'name': self.name,
            'coach': self.coach.to_simple(),
            'race': self.race,
            'treasury': self.treasury,
            'apothecary': self.apothecary,
            'rerolls': self.rerolls,
            'ass_coaches': self.ass_coaches,
            'players': players,
            'players_by_id': players_by_id
        }

    def init(self):
        self.players_by_id = {}
        for player in self.players:
            self.players_by_id[player.player_id] = player
        self.player_ids = [player.player_id for player in self.players]

    def get_player_by_id(self, player_id):
        return self.players_by_id[player_id]

    def has_player_by_id(self, player_id):
        return player_id in self.players_by_id

    def get_player_ids(self):
        return self.player_ids


class Outcome:

    def __init__(self, outcome_type, pos=None, player_id=None, opp_player_id=None, rolls=[], team_home=None, n=0):
        self.outcome_type = outcome_type
        self.pos = pos
        self.player_id = player_id
        self.opp_player_id = opp_player_id
        self.rolls = rolls
        self.team_home = team_home
        self.n = n

    def to_simple(self):
        rolls = []
        for roll in self.rolls:
            rolls.append(roll.to_simple())
        return {
            'outcome_type': self.outcome_type.name,
            'pos': self.pos.to_simple() if self.pos is not None else None,
            'player_id': self.player_id,
            'opp_player_id': self.opp_player_id,
            'rolls': rolls,
            'team_home': self.team_home if self.team_home is not None else None,
            #'n': self.n if self.n is not None else None
        }


class Inducement:

    def __init__(self, name, cost, max_num, reduced=0):
        self.name = name
        self.cost = cost
        self.max_num = max_num
        self.reduced = reduced


class RuleSet:

    def __init__(self, name, races=[], star_players=[], inducements=[], spp_actions={}, spp_levels={}, improvements={}, se_start=0, se_interval=0, se_pace=0):
        self.name = name
        self.races = races
        self.star_players = star_players
        self.inducements = inducements
        self.spp_actions = spp_actions
        self.spp_levels = spp_levels
        self.improvements = improvements
        self.se_start = se_start
        self.se_interval = se_interval
        self.se_pace = se_pace

    def get_position(self, position, race):
        for r in self.races:
            if r.name == race:
                for p in r.positions:
                    if p.name == position:
                        return p
                raise Exception("Position not found in race: " + race + " -> " + position)
        raise Exception("Race not found: " + race)
