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
        self.pitch_max = 11
        self.pitch_min = 3
        self.scrimmage_max = 3
        self.wing_max = 2
        self.rounds = 8
        self.kick_off_table = True
        self.fast_mode = False


class PlayerState:

    def __init__(self):
        self.ready = PlayerReadyState.READY
        self.spp_earned = 0
        self.moves = 0
        self.casualty_effect = None
        self.casualty_type = None

    def to_simple(self):
        return {
            'player_ready_state': self.ready.name,
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
            'score': self.score,
            'turn': self.turn,
            'rerolls_start': self.rerolls_start,
            'rerolls': self.rerolls,
            'ass_coaches': self.ass_coaches,
            'cheerleaders': self.cheerleaders,
            'fame': self.fame,
            'reroll_used': self.reroll_used
        }

    def reset_turn(self):
        self.reroll_used = False

    def use_reroll(self):
        self.rerolls -= 1
        self.reroll_used = True


class GameState:

    def __init__(self, game):
        self.game = game
        self.stack = Stack()
        self.reports = []
        self.half = 1
        self.round = 0
        self.kicking_first_half = None
        self.receiving_first_half = None
        self.kicking_this_drive = None
        self.receiving_this_drive = None
        self.current_team = None
        self.pitch = Pitch(game)
        self.dugouts = {team.team_id: Dugout(team) for team in game.teams}
        self.weather = WeatherType.NICE
        self.gentle_gust = False
        self.turn_order = []
        self.spectators = 0
        self.active_player = None

    def get_dugout(self, team):
        return self.dugouts[team.team_id]

    def to_simple(self):
        return {
            'half': self.half,
            'kicking_first_half': self.kicking_first_half.team_id if
            self.kicking_first_half.team_id is None else None,
            'receiving_first_half': self.receiving_first_half.team_id if
            self.receiving_first_half.team_id is None else None,
            'kicking_this_drive': self.kicking_this_drive.team_id if
            self.kicking_this_drive.team_id is None else None,
            'receiving_first_half': self.receiving_this_drive.team_id if
            self.receiving_this_drive.team_id is None else None,
            'pitch': self.pitch.to_simple(),
            'dugout': {team_id: dugout.to_simple() for team_id, dugout in self.dugouts.items()},
            'weather': self.weather.name,
            'gentle_gust': self.gentle_gust,
            'current_team': self.current_team,
            'round': self.round,
            'turn_order': self.turn_order,
            'spectators': self.spectators,
            'active_player_id': self.active_player.player_id
        }


class Ball:

    def __init__(self, position, on_ground=True, carried=False):
        self.position = position
        self.on_ground = on_ground
        self.carried = carried

    def move(self, x, y):
        self.position = Square(self.position.x + x, self.position.y + y)

    def move_to(self, pos):
        self.position = Square(pos.x, pos.y)

    def to_simple(self):
        return {
            'position': self.position.to_simple(),
            'on_ground': self.on_ground,
            'carried': self.carried
        }


class Pitch:

    def __init__(self, game):
        self.player_positions = {}
        self.game = game
        self.balls = []
        self.board = []
        for y in range(len(game.arena.board)):
            self.board.append([])
            for x in range(len(game.arena.board[y])):
                self.board[y].append(None)

    def to_simple(self):
        return {
            'board': self.board,
            'balls': [ball.to_simple() for ball in self.balls]
        }

    def put(self, piece, pos):
        piece.position = pos
        self.board[pos.y][pos.x] = piece

    def remove(self, piece):
        assert piece.position is not None
        self.board[piece.position.y][piece.position.x] = None
        piece.position = None

    def move(self, piece, pos_to):
        assert piece.position is not None
        assert self.board[pos_to.y][pos_to.x] is None
        for ball in self.balls:
            if ball.position == piece.position and ball.is_carried:
                ball.move_to(pos_to)
        self.remove(piece)
        self.put(piece, pos_to)

    def swap(self, piece_a, piece_b):
        assert piece_a.position is not None
        assert piece_b.position is not None
        pos_a = Square(piece_a.position.x, piece_a.position.y)
        pos_b = Square(piece_b.position.x, piece_b.position.y)
        piece_a.position = pos_b
        piece_b.position = pos_a
        self.board[pos_a.y][pos_a.x] = piece_b
        self.board[pos_b.y][pos_b.x] = piece_a

    def is_setup_legal(self, team, tile=None, max_players=11, min_players=3):
        cnt = 0
        for y in range(len(self.board)):
            for x in range(len(self.board[y])):
                if not self.game.arena.is_team_side(Square(x, y), team):
                    continue
                if tile is None or self.game.arena.board[y][x] == tile:
                    piece = self.board[y][x]
                    if piece is Player and piece.team == team:
                        cnt += 1
        if cnt > max_players or cnt < min_players:
            return False
        return True

    def is_setup_legal_scrimmage(self, team, min_players=3):
        if team:
            return self.is_setup_legal(team, tile=Tile.HOME_SCRIMMAGE, min_players=min_players)
        return self.is_setup_legal(team, tile=Tile.AWAY_SCRIMMAGE, min_players=min_players)

    def is_setup_legal_wings(self, team, min_players=0, max_players=2):
        if team:
            return self.is_setup_legal(team, tile=Tile.HOME_WING_LEFT, max_players=max_players, min_players=min_players) and \
                   self.is_setup_legal(team, tile=Tile.HOME_WING_RIGHT, max_players=max_players, min_players=min_players)
        return self.is_setup_legal(team, tile=Tile.AWAY_WING_LEFT, max_players=max_players, min_players=min_players) and \
               self.is_setup_legal(team, tile=Tile.AWAY_WING_RIGHT, max_players=max_players, min_players=min_players)

    def get_balls_at(self, pos, in_air=False):
        balls = []
        for ball in self.balls:
            if ball.position == pos and (ball.on_ground or in_air):
                balls.append(ball)
        return balls

    def get_ball_at(self, pos, in_air=False):
        """
        Assumes there is only one ball on the square
        :param pos:
        :param in_air:
        :return: Ball or None
        """
        for ball in self.balls:
            if ball.position == pos and (ball.on_ground or in_air):
                return ball
        return None

    def get_ball_positions(self):
        return [ball.position for ball in self.balls]

    def get_ball_position(self):
        """
        Assumes there is only one ball on the square
        :return: Ball or None
        """
        for ball in self.balls:
            return ball.position
        return None

    def is_out_of_bounds(self, pos):
        return pos.x < 1 or pos.x >= len(self.board[0])-1 or pos.y < 1 or pos.y >= len(self.board)-1

    def get_player_at(self, pos):
        return self.board[pos.y][pos.x]

    def get_push_squares(self, pos_from, pos_to):
        squares_to = self.game.state.pitch.get_adjacent_squares(pos_to, include_out=True)
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
                if self.get_player_at(square) is None:
                    squares_empty.append(square)
                if self.is_out_of_bounds(square):
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
                if exclude_occupied and self.get_player_at(sq) is not None:
                    continue
                if not manhattan:
                    squares.append(sq)
                elif xx == 0 or yy == 0:
                    squares.append(sq)
        return squares

    def adjacent_player_squares_at(self, player, position, include_own=True, include_opp=True, manhattan=False, only_blockable=False, only_foulable=False):
        squares = []
        for square in self.get_adjacent_squares(position, manhattan=manhattan):
            player_at = self.get_player_at(square)
            if player_at is None:
                continue
            if include_own and player_at.team == player.team or include_opp and not player_at.team == player.team:
                if not only_blockable or player_at.ready in Rules.blockable:
                    if not only_foulable or player_at.ready in Rules.foulable:
                        squares.append(square)
        return squares

    def adjacent_player_squares(self, player, include_own=True, include_opp=True, manhattan=False, only_blockable=False, only_foulable=False):
        return self.adjacent_player_squares_at(player, player.position, include_own, include_opp, manhattan, only_blockable, only_foulable)

    def num_tackle_zones_at(self, player, position):
        tackle_zones = 0
        for square in self.adjacent_player_squares_at(player, position, include_own=False, include_opp=True):
            player = self.get_player_at(square)
            if player is not None and player.has_tackle_zone():
                tackle_zones += 1
        return tackle_zones

    def num_tackle_zones_in(self, player):
        tackle_zones = 0
        for square in self.adjacent_player_squares(player, include_own=False, include_opp=True):
            player = self.get_player_at(square)
            if player is not None and player.has_tackle_zone():
                tackle_zones += 1
        return tackle_zones

    def tackle_zones_detailed(self, player):
        tackle_zones = 0
        tacklers = []
        prehensile_tailers = []
        diving_tacklers = []
        shadowers = []
        tentaclers = []
        for square in self.adjacent_player_squares(player.position, include_own=False, include_opp=True):
            player_at = self.get_player_at(square)
            if player_at is not None and player_at.has_tackle_zone():
                tackle_zones += 1
            if player_at is None and player_at.has_skill(Skill.TACKLE):
                tacklers.append(player_at)
            if player_at is None and player_at.has_skill(Skill.PREHENSILE_TAIL):
                prehensile_tailers.append(player_at)
            if player_at is None and player_at.has_skill(Skill.DIVING_TACKLE):
                diving_tacklers.append(player_at)
            if player_at is None and player_at.has_skill(Skill.SHADOWING):
                shadowers.append(player_at)
            if player_at is None and player_at.has_skill(Skill.TENTACLES):
                tentaclers.append(player_at)

        return tackle_zones, tacklers, prehensile_tailers, diving_tacklers, shadowers, tentaclers

    def assists(self, player, opp_player, ignore_guard=False):
        assists = []
        for yy in range(-1, 2, 1):
            for xx in range(-1, 2, 1):
                if yy == 0 and xx == 0:
                    continue
                p = Square(opp_player.position.x+xx, opp_player.position.y+yy)
                if not self.is_out_of_bounds(p) and player.position != p:
                    player_at = self.get_player_at(p)
                    if player_at is not None:
                        if player_at.team == player.team:
                            if player_at.state.ready not in Rules.assistable:
                                continue
                            if (not ignore_guard and player_at.has_skill(Skill.GUARD)) or \
                                            self.num_tackle_zones_in(player_at) <= 1:
                                # TODO: Check if attacker has a tackle zone
                                assists.append(player_at)
        return assists

    def passes(self, player, pos_from):
        squares = []
        distances = []
        distances_allowed = [PassDistance.QUICK_PASS,
                             PassDistance.SHORT_PASS,
                             PassDistance.LONG_PASS,
                             PassDistance.LONG_BOMB,
                             PassDistance.HAIL_MARY] if Skill.HAIL_MARY_PASS in player.get_skills() \
            else [PassDistance.QUICK_PASS, PassDistance.SHORT_PASS, PassDistance.LONG_PASS, PassDistance.LONG_BOMB]
        if self.game.state.weather == WeatherType.BLIZZARD:
            distances_allowed = [PassDistance.QUICK_PASS, PassDistance.SHORT_PASS]
        for pos in self.game.state.pitch.positions:
            if self.is_out_of_bounds(pos) or pos_from == pos:
                continue
            distance = self.pass_distance(pos_from, pos)
            if distance in distances_allowed:
                squares.append(pos)
                distances.append(distance)
        return squares, distances

    def pass_distance(self, passer, pos):
        distance_x = abs(passer.position.x - pos.x)
        distance_y = abs(passer.position.y - pos.y)
        if distance_y >= len(Rules.pass_matrix) or distance_x >= len(Rules.pass_matrix[0]):
            return PassDistance.HAIL_MARY
        distance = Rules.pass_matrix[distance_y][distance_x]
        return PassDistance(distance)

    def interceptors(self, passer, pos):
        """
        1) Find line x from a to b
        2) Find squares s where x intersects
        3) Find manhattan neighboring n squares of s
        4) Remove squares where distance to a is larger than dist(a,b)
        5) Remove squares without standing opponents with hands
        6) Determine players on squares
        """

        # 1) Find line x from a to b
        x = get_line((passer.position.x, passer.position.y), (pos.x, pos.y))

        # 2) Find squares s where x intersects
        s = []
        for i in x:
            s.append(Square(i[0], i[1]))

        # 3) Include manhattan neighbors s into n
        # 4) Remove squares where distance to a is larger than dist(a,b)
        max_distance = passer.position.distance(pos)
        n = set()
        for square in s:
            for neighbor in self.get_adjacent_squares(square) + [square]:

                if neighbor in n:
                    continue

                # 4) Remove squares where distance to a is larger than dist(a,b)
                if neighbor.distance(passer.position) > max_distance:
                    continue
                if neighbor.distance(pos) > max_distance:
                    continue
                if neighbor.x > max(passer.position.x, pos.x) or neighbor.x < min(passer.position.x, pos.x):
                    continue
                if neighbor.y > max(passer.position.y, pos.y) or neighbor.y < min(passer.position.y, pos.y):
                    continue

                # 5) Remove squares without standing opponents with hands
                player_at = self.get_player_at(neighbor)
                if player_at is None:
                    continue
                if player_at.team != passer.team:
                    continue
                if self.game.state.get_player_ready_state(player_at, player_at.team) not in Rules.catchable:
                    continue
                if self.game.get_player(player_at).has_skill(Skill.NO_HANDS):
                    continue

                n.add(neighbor)

        if passer.position in n:
            n.remove(pos)
        if pos in n:
            n.remove(pos)

        players = []
        for square in n:
            players.append(self.get_player_at(square))

        return players


class ActionChoice:

    def __init__(self, action_type, team, positions=None, players=None, indexes=None, rolls=None, block_rolls=None, dice=None, agi_rolls=None, disabled=False):
        self.action_type = action_type
        self.positions = positions
        self.players = players
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
            'player_ids': [player.player_id for player in self.players],
            'team_id': self.team.team_id if self.team is not None else None,
            'indexes': self.indexes,
            "rolls": self.rolls,
            "block_rolls": self.block_rolls,
            "agi_rolls": self.agi_rolls,
            "dice": [die.to_simple() for die in self.dice],
            "disabled": self.disabled
        }


class Action:

    def __init__(self, action_type, pos_from=None, pos_to=None, player_from_id=None, player_to_id=None, idx=0,
                 team_id=None):
        self.action_type = action_type
        self.pos_from = pos_from
        self.pos_to = pos_to
        self.player_from_id = player_from_id
        self.player_to_id = player_to_id
        self.idx = idx
        self.team_id = team_id

    def to_simple(self):
        return {
            'action_type': self.action_type.name,
            'position': self.pos_from.to_simple() if self.pos_from is not None else None
        }


class TwoPlayerArena:

    home_tiles = [Tile.HOME, Tile.HOME_TOUCHDOWN, Tile.HOME_WING_LEFT, Tile.HOME_WING_RIGHT, Tile.HOME_SCRIMMAGE]
    away_tiles = [Tile.AWAY, Tile.AWAY_TOUCHDOWN, Tile.AWAY_WING_LEFT, Tile.AWAY_WING_RIGHT, Tile.AWAY_SCRIMMAGE]
    scrimmage_tiles = [Tile.HOME_SCRIMMAGE, Tile.AWAY_SCRIMMAGE]
    wing_right_tiles = [Tile.HOME_WING_RIGHT, Tile.AWAY_WING_RIGHT]
    wing_left_tiles = [Tile.HOME_WING_LEFT, Tile.AWAY_WING_LEFT]
    team_td_tiles = [Tile.HOME_TOUCHDOWN]

    def __init__(self, game, board):
        self.game = game
        self.board = board
        self.json = None

    def to_simple(self):
        if self.json is not None:
            return self.json

        board = []
        for _ in self.board:
            board.append([])
            for tile in self.board[0]:
                board[-1].append(str(tile))
        self.json = {
            'board': board
        }
        return self.json

    def is_team_side(self, pos, team):
        if team == self.game.home_team:
            return self.board[pos.y][pos.x] in TwoPlayerArena.home_tiles
        return self.board[pos.y][pos.x] in TwoPlayerArena.away_tiles

    def get_team_side(self, team):
        tiles = []
        for y in range(len(self.board)):
            for x in range(len(self.board[y])):
                if self.board[y][x] in (TwoPlayerArena.home_tiles if team == self.game.home_team else TwoPlayerArena.away_tiles):
                    tiles.append(Square(x, y))
        return tiles

    def is_scrimmage(self, pos):
        return self.board[pos.y][pos.x] in TwoPlayerArena.scrimmage_tiles

    def is_touchdown(self, player):
        if player.team == self.game.home_team:
            return self.board[player.position.y][player.position.x] == Tile.AWAY_TOUCHDOWN
        return self.board[player.position.y][player.position.x] == Tile.HOME_TOUCHDOWN

    def is_wing(self, pos, right):
        if right:
            return self.board[pos.y][pos.x] in TwoPlayerArena.wing_right_tiles
        return self.board[pos.y][pos.x] in TwoPlayerArena.wing_left_tiles


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
            'result': self.get_result(),
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

    def get_result(self):
        return self.sum + self.modifiers

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

    def __init__(self, team):
        self.team = team
        self.reserves = []
        self.kod = []
        self.casualties = []
        self.dungeon = []  # Ejected

    def to_simple(self):
        return {
            'team_id': self.team.team_id,
            'reserves': [player.player_id for player in self.reserves],
            'kod': [player.player_id for player in self.kod],
            'casualties': [player.player_id for player in self.casualties],
            'dungeon': [player.player_id for player in self.dungeon]
        }


class Position:

    def __init__(self, name, races, ma, st, ag, av, skills, cost, feeder, n_skill_sets=[], d_skill_sets=[],
                 star_player=False):
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


class Piece:

    def __init__(self, position=None):
        self.position = position


class Player(Piece):

    def __init__(self, player_id, role, name, nr, team, extra_skills=[], extra_ma=0, extra_st=0, extra_ag=0, extra_av=0,
                 niggling=0, mng=False, spp=0, position=None):
        super().__init__(position)
        self.player_id = player_id
        self.role = role
        self.name = name
        self.nr = nr
        self.team = team
        self.extra_skills = extra_skills
        self.skills = self.extra_skills + self.role.skills
        self.extra_ma = extra_ma
        self.extra_st = extra_st
        self.extra_ag = extra_ag
        self.extra_av = extra_av
        self.niggling = niggling
        self.mng = mng
        self.spp = spp
        self.state = PlayerState()

    def get_ag(self):
        return self.role.ag + self.extra_ag

    def get_st(self):
        return self.role.st + self.extra_st

    def get_ma(self):
        return self.role.ma + self.extra_ma

    def get_av(self):
        return self.role.av + self.extra_av

    def has_skill(self, skill):
        return skill in self.skills

    def get_skills(self):
        return self.skills

    def has_tackle_zone(self,):
        if self.state.ready not in Rules.has_tackle_zone:
            return False
        if self.has_skill(Skill.TITCHY):
            return False
        return True

    def to_simple(self):
        skills = []
        for skill in self.get_skills():
            skills.append(skill.name)
        return {
            'player_id': self.player_id,
            'name': self.name,
            'role': self.role.name,
            'nr': self.nr,
            'skills': self.skills,
            'ma': self.get_ma(),
            'st': self.get_st(),
            'ag': self.get_ag(),
            'av': self.get_av(),
            'niggling': self.niggling,
            'mng': self.mng,
            'spp': self.spp,
            'state': self.state.to_simple(),
            'position': self.position
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
        self.state = TeamState(self)

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


class Outcome:

    def __init__(self, outcome_type, pos=None, player=None, opp_player=None, rolls=[], team=None, n=0, skill=None):
        self.outcome_type = outcome_type
        self.pos = pos
        self.player = player
        self.opp_player = opp_player
        self.rolls = rolls
        self.team = team
        self.n = n
        self.skill = skill

    def to_simple(self):
        rolls = []
        for roll in self.rolls:
            rolls.append(roll.to_simple())
        return {
            'outcome_type': self.outcome_type.name,
            'pos': self.pos.to_simple() if self.pos is not None else None,
            'player': self.player.player_id if self.player is not None else None,
            'opp_player': self.opp_player.player_id if self.opp_player is not None else None,
            'rolls': rolls,
            'team_id': self.team.team_id if self.team is not None else None,
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
