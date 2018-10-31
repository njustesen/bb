import numpy as np
import secrets
import random
from math import sqrt
from bb.core.util import *
from bb.core.table import *


class Configuration:

    def __init__(self):
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


class PlayerState:

    def __init__(self):
        self.player_ready_state = PlayerReadyState.READY
        self.spp_earned = 0
        self.moves = 0
        self.casualty_effect = None
        self.casualty_type = None

    def to_simple(self):
        return {
            'player_ready_state': self.player_ready_state.name,
            'spp_earned': self.spp_earned,
            'moves': self.moves,
            'casualty_type': self.casualty_type.name if self.casualty_type is not None else None,
            'casualty_effect': self.casualty_effect.name if self.casualty_effect is not None else None
        }


class TeamState:

    def __init__(self, team):
        self.bribes = 0
        self.babes = 0
        self.apothecary_available = team.apothecary
        self.wizard_available = False
        self.masterchef = False
        self.player_states = {player.player_id: PlayerState() for player in team.players}
        self.score = 0
        self.turn = 0
        self.rerolls_start = team.rerolls
        self.rerolls = team.rerolls
        self.ass_coaches = team.ass_coaches
        self.cheerleaders = team.cheerleaders
        self.fame = 0
        self.reroll_used = False

    def to_simple(self):
        return {
            'bribes': self.bribes,
            'babes': self.babes,
            'apothecary_available': self.apothecary_available,
            'masterchef': self.masterchef,
            'player_states': {player_id: player_state.to_simple() for player_id, player_state in self.player_states.items()},
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

    def reset_turn(self, reset_rerolls=True):
        if reset_rerolls:
            self.reroll_used = False
        for player_id, player_state in self.player_states.items():
            self.player_states[player_id].moves = 0
            if player_state.player_ready_state == PlayerReadyState.USED:
                self.player_states[player_id].player_ready_state = PlayerReadyState.READY
            elif player_state.player_ready_state == PlayerReadyState.DOWN_USED:
                self.player_states[player_id].player_ready_state = PlayerReadyState.DOWN_READY

    def use_reroll(self):
        self.rerolls -= 1
        self.reroll_used = True

    def injure_player(self, player_id, casualty, casualty_effect):
        print("casualty_effect={}".format(casualty_effect))
        self.player_states[player_id].casualty = casualty
        self.player_states[player_id].casualty_effect = casualty_effect


class GameState:

    def __init__(self, game):
        self.game = game
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
        self.spectators = 0
        self.active_player_id = None

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
            'team_turn': self.team_turn,
            'spectators': self.spectators,
            'active_player_id': self.active_player_id
        }

    def reset_turn(self, home):
        self.team_turn = None
        self.get_team_state(home).reset_turn(reset_rerolls=True)
        self.get_team_state(not home).reset_turn(reset_rerolls=False)

    def reset_kickoff(self):
        self.team_turn = None
        self.home_state.reset_turn()
        self.away_state.reset_turn()

    def reset_half(self, home):
        self.team_turn = None
        self.get_team_state(home).reset_half()

    def get_player_state(self, player_id, home):
        return self.get_team_state(home).player_states[player_id]

    def get_player_ready_state(self, player_id, home):
        return self.get_team_state(home).player_states[player_id].player_ready_state

    def set_player_ready_state(self, player_id, home, player_ready_state):
        self.get_team_state(home).player_states[player_id].player_ready_state = player_ready_state

    def get_team_state(self, home):
        return self.home_state if home else self.away_state

    def get_dugout(self, home):
        return self.home_dugout if home else self.away_dugout

    def knock_out(self, player_id):
        home = self.game.get_home_by_player_id(player_id)
        self.get_team_state(home).player_states[player_id] = PlayerReadyState.KOD
        self.field.remove(player_id)
        self.get_dugout(home).kod.append(player_id)

    def casualty(self, player_id, home, player_state, effect):
        self.set_player_ready_state(player_id, home, player_state)
        self.field.remove(player_id)
        self.get_dugout(home).casualties.append(player_id)
        self.game.state.get_team_state(home).injure_player(player_id, effect)

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
        self.ball_in_control = False
        self.game = game
        self.board = []
        self.positions = []
        for y in range(len(game.arena.board)):
            for x in range(len(game.arena.board[y])):
                self.positions.append(Square(x, y))
        for y in range(len(game.arena.board)):
            row = []
            for x in range(len(game.arena.board[y])):
                row.append(None)
            self.board.append(row)

    def to_simple(self):
        ball = None
        if self.ball_position is not None:
            ball = self.ball_position.to_simple()
        return {
            'ball_position': ball,
            'ball_in_air': self.ball_in_air,
            'board': self.board,
            'ball_in_control': self.ball_in_control
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
            self.ball_position = Square(pos_to.x, pos_to.y)
        if self.board[pos_to.y][pos_to.x] is not None:
            raise Exception("Player cannot be moved on top of another player")
        self.board[pos_from.y][pos_from.x] = None
        self.board[pos_to.y][pos_to.x] = player_id
        self.player_positions[player_id] = Square(pos_to.x, pos_to.y)

    def swap(self, pos_from, pos_to):
        """
        :param pos_from: A position on the field
        :param pos_to: A position on the field
        :return:
        """
        player_from_id = self.board[pos_from.y][pos_from.x]
        if player_from_id in self.player_positions:
            self.player_positions[player_from_id] = Square(pos_to.x, pos_to.y)

        player_to_id = self.board[pos_to.y][pos_to.x]
        if player_to_id is not None:
            self.player_positions[player_to_id] = Square(pos_from.x, pos_from.y)
        self.board[pos_to.y][pos_to.x] = player_from_id
        self.board[pos_from.y][pos_from.x] = player_to_id

    def has_ball(self, player_id):
        if self.ball_in_control:
            return self.ball_position is not None and self.ball_position == self.get_player_position(player_id)

    def get_player_id_at(self, pos):
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

    def get_team_player_ids(self, home, state=None, only_field=False):
        player_ids = []
        for player_id in self.game.get_team(home).players_by_id.keys():
            if state is None or self.game.state.get_player_ready_state(player_id, home) == state:
                if not only_field or player_id in self.player_positions.keys():
                    player_ids.append(player_id)
        return player_ids

    def get_random_player(self, home):
        return secrets.choice(self.get_team_player_ids(home))

    def is_ball_at(self, pos, in_air=False):
        return self.ball_position == pos and in_air == self.ball_in_air

    def move_ball(self, pos, in_air=False, control=True):
        self.ball_position = pos
        self.ball_in_air = in_air
        self.ball_in_control = control

    def is_ball_out(self):
        return self.is_out_of_bounds(self.ball_position)

    def is_out_of_bounds(self, pos):
        return pos.x < 1 or pos.x >= len(self.board[0])-1 or pos.y < 1 or pos.y >= len(self.board)-1

    def has_tackle_zone(self, player, home):
        if self.game.state.get_player_ready_state(player.player_id, home) not in Rules.has_tackle_zone:
            return False
        if player.has_skill(Skill.TITCHY):
            return False
        return True

    def get_push_squares(self, pos_from, pos_to):
        squares_to = self.game.state.field.get_adjacent_squares(pos_to, include_out=True)
        squares_empty = []
        squares_out = []
        squares = []
        print("From:", pos_from)
        for square in squares_to:
            print("Checking: ", square)
            print("Distance: ", pos_from.distance(square, manhattan=False))
            include = False
            if pos_from.x == pos_to.x or pos_from.y == pos_to.y:
                if pos_from.distance(square, manhattan=False) >= 2:
                    include = True
            else:
                if pos_from.distance(square, manhattan=True) >= 3:
                    include = True
            print("Include: ", include)
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

    def get_adjacent_squares(self, pos, manhattan=False, include_out=False, exclude_occupied=False):
        squares = []
        for yy in [-1, 0, 1]:
            for xx in [-1, 0, 1]:
                if yy == 0 and xx == 0:
                    continue
                sq = Square(pos.x+xx, pos.y+yy)
                if not include_out and self.is_out_of_bounds(sq):
                    continue
                if exclude_occupied and self.get_player_id_at(sq) is not None:
                    continue
                if not manhattan:
                    squares.append(sq)
                elif xx == 0 or yy == 0:
                    squares.append(sq)
        return squares

    def get_adjacent_player_squares(self, pos, include_home=True, include_away=True, manhattan=False, only_blockable=False, only_foulable=False):
        squares = []
        for square in self.get_adjacent_squares(pos, manhattan=manhattan):
            player_id = self.get_player_id_at(square)
            if player_id is None:
                continue
            team_home = self.game.get_home_by_player_id(player_id)
            if include_home and team_home or include_away and not team_home:
                if not only_blockable or self.game.state.get_player_ready_state(player_id, team_home) in Rules.blockable:
                    if not only_foulable or self.game.state.get_player_ready_state(player_id, team_home) in Rules.foulable:
                        squares.append(square)
        return squares

    def get_tackle_zones(self, pos, home):
        tackle_zones = 0
        for square in self.get_adjacent_player_squares(pos, include_home=not home, include_away=home):
            player_id = self.get_player_id_at(square)
            player = self.game.get_player(player_id)
            if player_id is not None and self.has_tackle_zone(player, not home):
                tackle_zones += 1
        return tackle_zones

    def get_tackle_zones_detailed(self, pos):
        tackle_zones = 0
        tackle_ids = []
        prehensile_tail_ids = []
        diving_tackle_ids = []
        shadowing_ids = []
        tentacles_ids = []
        own_player_id = self.game.state.field.get_player_id_at(pos)
        own_home = self.game.get_home_by_player_id(own_player_id)
        for square in self.get_adjacent_player_squares(pos, include_home=not own_home, include_away=own_home):
            player_id = self.get_player_id_at(square)
            player = self.game.get_player(player_id)
            home = self.game.get_home_by_player_id(player_id) if player_id is not None else None
            if player_id is not None and self.has_tackle_zone(player, home):
                tackle_zones += 1
            if player_id is None and player.has_skill(Skill.TACKLE):
                tackle_ids.append(player_id)
            if player_id is None and player.has_skill(Skill.PREHENSILE_TAIL):
                prehensile_tail_ids.append(player_id)
            if player_id is None and player.has_skill(Skill.DIVING_TACKLE):
                diving_tackle_ids.append(player_id)
            if player_id is None and player.has_skill(Skill.SHADOWING):
                shadowing_ids.append(player_id)
            if player_id is None and player.has_skill(Skill.TENTACLES):
                tentacles_ids.append(player_id)

        return tackle_zones, tackle_ids, prehensile_tail_ids, diving_tackle_ids, shadowing_ids, tentacles_ids

    def assists(self, home, player_from, player_to, ignore_guard=False):
        pos_from = self.get_player_position(player_from.player_id)
        pos_to = self.get_player_position(player_to.player_id)
        assists = []
        for yy in range(-1, 2, 1):
            for xx in range(-1, 2, 1):
                if yy == 0 and xx == 0:
                    continue
                p = Square(pos_to.x+xx, pos_to.y+yy)
                if not self.is_out_of_bounds(p) and pos_from != p:
                    player_id = self.get_player_id_at(p)
                    if player_id is not None:
                        if self.game.get_home_by_player_id(player_id) == home:
                            if self.game.state.get_player_ready_state(player_id, home) not in Rules.assistable:
                                continue
                            if (not ignore_guard and self.game.get_player(player_id).has_skill(Skill.GUARD)) or \
                                            self.get_tackle_zones(p, home=home) <= 1:  # TODO: Check if attacker has a tackle zone
                                assists.append(player_id)
        return assists

    def get_passes(self, player_from, pos_from):
        squares = []
        distances = []
        distances_allowed = [PassDistance.QUICK_PASS, PassDistance.SHORT_PASS, PassDistance.LONG_PASS, PassDistance.LONG_BOMB, PassDistance.HAIL_MARY] if Skill.HAIL_MARY_PASS in player_from.get_skills() \
            else [PassDistance.QUICK_PASS, PassDistance.SHORT_PASS, PassDistance.LONG_PASS, PassDistance.LONG_BOMB]
        if self.game.state.weather == WeatherType.BLIZZARD:
            distances_allowed = [PassDistance.QUICK_PASS, PassDistance.SHORT_PASS]
        for pos in self.game.state.field.positions:
            if self.is_out_of_bounds(pos) or pos_from == pos:
                continue
            distance = self.pass_distance(pos_from, pos)
            if distance in distances_allowed:
                squares.append(pos)
                distances.append(distance)
        return squares, distances

    def pass_distance(self, pos_from, pos_to):
        distance_x = abs(pos_from.x - pos_to.x)
        distance_y = abs(pos_from.y - pos_to.y)
        if distance_y >= len(Rules.pass_matrix) or distance_x >= len(Rules.pass_matrix[0]):
            return PassDistance.HAIL_MARY
        distance = Rules.pass_matrix[distance_y][distance_x]
        if distance == 5:
            return PassDistance.HAIL_MARY
        return PassDistance(distance)

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
            for neighbor in self.get_adjacent_squares(square) + [square]:

                if neighbor in n:
                    continue

                # 4) Remove squares where distance to a is larger than dist(a,b)
                if neighbor.distance(pos_from) > max_distance:
                    continue
                if neighbor.distance(pos_to) > max_distance:
                    continue
                if neighbor.x > max(pos_from.x, pos_to.x) or neighbor.x < min(pos_from.x, pos_to.x):
                    continue
                if neighbor.y > max(pos_from.y, pos_to.y) or neighbor.y < min(pos_from.y, pos_to.y):
                    continue

                # 5) Remove squares without standing opponents with hands
                player_at = self.get_player_id_at(neighbor)
                player_home = self.game.get_home_by_player_id(player_at)
                if player_at is None:
                    continue
                if player_home != home:
                    continue
                if self.game.state.get_player_ready_state(player_at, player_home) not in Rules.catchable:
                    continue
                if self.game.get_player(player_at).has_skill(Skill.NO_HANDS):
                    continue

                n.add(neighbor)

        if pos_from in n:
            n.remove(pos_from)
        if pos_to in n:
            n.remove(pos_to)

        players = []
        for square in n:
            players.append(self.get_player_id_at(square))

        return players


class ActionChoice:

    def __init__(self, action_type, team, positions=[], player_ids=[], indexes=[], rolls=[], block_rolls=[], dice=[], disabled=False, agi_rolls=[]):
        self.action_type = action_type
        self.positions = positions
        self.player_ids = player_ids
        self.team = team
        self.indexes = indexes
        self.rolls = rolls
        self.block_rolls = block_rolls
        self.dice = dice
        self.disabled = disabled
        self.agi_rolls = agi_rolls

    def to_simple(self):
        return {
            'action_type': self.action_type.name,
            'positions': [position.to_simple() if position is not None else None for position in self.positions],
            'player_ids': self.player_ids,
            'team': self.team,
            'indexes': self.indexes,
            "rolls": self.rolls,
            "block_rolls": self.block_rolls,
            "agi_rolls": self.agi_rolls,
            "dice": [die.to_simple() for die in self.dice],
            "disabled": self.disabled
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
    home_td_tiles = [Tile.HOME_TOUCHDOWN]

    def __init__(self, board):
        self.board = board
        self.json = None

    def to_simple(self):
        if self.json is not None:
            return self.json

        board = []
        for row in self.board:
            board.append([])
            for tile in self.board[0]:
                board[-1].append(str(tile))
        self.json = {
            'board': board
        }
        return self.json

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
        :return: Whether pos is within team's touchdown zone (where they score)
        """
        if team:
            return self.board[pos.y][pos.x] == Tile.AWAY_TOUCHDOWN

        return self.board[pos.y][pos.x] == Tile.HOME_TOUCHDOWN

    def is_wing(self, pos, right):
        if right:
            return self.board[pos.y][pos.x] in Arena.wing_right_tiles
        return self.board[pos.y][pos.x] in Arena.wing_left_tiles


class Die:

    def get_value(self):
        pass


class DiceRoll:

    def __init__(self, dice, modifiers=0, target=None, d68=False, roll_type=RollType.AGILITY_ROLL):
        self.dice = dice
        self.sum = 0
        self.d68 = d68
        self.target = target
        self.modifiers = modifiers
        self.roll_type = roll_type
        # Roll dice
        for d in self.dice:
            if not isinstance(d, BBDie):
                if d68 and isinstance(d, D6):
                    self.sum += d.get_value() * 10
                else:
                    self.sum += d.get_value()

    def to_simple(self):
        dice = []
        for die in self.dice:
            dice.append(die.to_simple())
        return {
            'dice': dice,
            'sum': self.sum,
            'target': self.target,
            'modifiers': self.modifiers,
            'modified_target': self.modified_target(),
            'roll_type': self.roll_type.name
        }

    def modified_target(self):
        if self.target is not None:
            return max(1*len(self.dice), min(6*len(self.dice), self.target - self.modifiers))
        return None

    def contains(self, value):
        for die in self.dice:
            if die.get_value() == value:
                return True
        return False

    def get_values(self):
        return [d.get_value() for d in self.dice]

    def get_sum(self):
        return self.sum

    def is_d6_success(self):
        if self.sum == 1:
            return False

        if self.sum == 6:
            return True

        return self.sum + self.modifiers >= self.target

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
        self.skills = self.extra_skills + self.position.skills
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
        return skill in self.skills

    def get_skills(self):
        return self.skills

    def to_simple(self):
        skills = []
        for skill in self.get_skills():
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
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return self.x * 1000 + self.y

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
                 cheerleaders=0, fan_factor=0):
        self.team_id = team_id
        self.name = name
        self.coach = coach
        self.race = race
        self.players = players
        self.treasury = treasury
        self.apothecary = apothecary
        self.rerolls = rerolls
        self.fan_factor = fan_factor
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
            'cheerleaders': self.cheerleaders,
            'fan_factor': self.fan_factor,
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

    def __init__(self, outcome_type, pos=None, player_id=None, opp_player_id=None, rolls=[], team_home=None, n=0, skill=None):
        self.outcome_type = outcome_type
        self.pos = pos
        self.player_id = player_id
        self.opp_player_id = opp_player_id
        self.rolls = rolls
        self.team_home = team_home
        self.n = n
        self.skill = skill

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
            'n': self.n if self.n is not None else None,
            'skill': self.skill.name if self.skill is not None else None
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
