import os
import numpy as np
import untangle
from .model import *
import json
from bb.core.util import *
import glob
import bb
import pkg_resources

arena_char_map = {
    'C': Tile.CROWD,
    'H': Tile.HOME,
    'a': Tile.AWAY,
    'S': Tile.HOME_SCRIMMAGE,
    's': Tile.AWAY_SCRIMMAGE,
    'L': Tile.HOME_WING_LEFT,
    'R': Tile.HOME_WING_RIGHT,
    'l': Tile.AWAY_WING_LEFT,
    'r': Tile.AWAY_WING_RIGHT,
    'E': Tile.HOME_TOUCHDOWN,
    'e': Tile.AWAY_TOUCHDOWN
}


def parse_sc(sc):

    parsed = []
    for cat in sc:
        if cat == "G":
            parsed.append(SkillCategory.General)
        elif cat == "A":
            parsed.append(SkillCategory.Agility)
        elif cat == "S":
            parsed.append(SkillCategory.Strength)
        elif cat == "P":
            parsed.append(SkillCategory.Passing)
        elif cat == "M":
            parsed.append(SkillCategory.Mutation)
        elif cat == "E":
            parsed.append(SkillCategory.Extraordinary)
    return parsed


def get_rule_set(name):

    path = get_data_path('rules/' + name)

    print("Loading rules at " + path)
    obj = untangle.parse(path)

    ruleset = RuleSet(path.split("/")[-1].split(".")[0])

    print("Parsing races")

    for r in obj.rules.rosters.roster:
        print("-- Parsing " + str(r.name.cdata))
        race = Race(r.name.cdata, [], (int)(r.rerollValue.cdata), (bool)(r.apothecary.cdata), (bool)(r.stakes.cdata))
        for p in r.positions.position:
            position = Position(p.title.cdata, [race.name], (int)(p.ma.cdata), (int)(p.st.cdata), (int)(p.ag.cdata), (int)(p.av.cdata), [], p.cost.cdata, parse_sc(p.normal.cdata), parse_sc(p.double.cdata))
            if len(p.skills) > 0:
                for skill_name in p.skills.skill:
                    position.skills.append(parse_enum(Skill, skill_name.cdata))
            race.positions.append(position)
        ruleset.races.append(race)

    print("Parsing star players")

    for star in obj.rules.stars.star:
        print("-- Parsing " + str(star.name.cdata))
        position = Position(star.name.cdata, [], (int)(star.ma.cdata), (int)(star.st.cdata), (int)(star.ag.cdata), (int)(star.av.cdata), [], star.cost.cdata, star.feeder, [], [], star_player=True)
        if len(star.skills) == 0:
            continue
        for skill_name in star.skills.skill:
            position.skills.append(parse_enum(Skill, skill_name.cdata))
        for race_name in star.races.race:
            position.races.append(race_name)
        ruleset.star_players.append(position)

    print("Parsing inducements")
    inducements = []
    for i in obj.rules.inducements.inducement:
        print("-- Parsing " + str(i["name"]))
        reduced = 0 if not "reduced" in i else i["reduced"]
        inducement = Inducement(i["name"], i.cdata, i["max"], reduced=reduced)
        ruleset.inducements.append(inducement)

    print("Parsing SPP actions")
    for a in obj.rules.spp.action:
        print("-- Parsing " + str(a["name"]))
        ruleset.spp_actions[a["name"]] = a.cdata

    print("Parsing SPP levels")
    for l in obj.rules.spp.level:
        print("-- Parsing " + str(l["name"]))
        ruleset.spp_actions[l["name"]] = l.cdata

    print("Parsing improvements")
    for imp in obj.rules.improvements.improvement:
        print("-- Parsing " + str(imp["name"]))
        ruleset.improvements[imp["name"]] = imp.cdata

    print("Parsing spiralling expenses")
    ruleset.se_start = obj.rules.spirallingExpenses.start.cdata
    ruleset.se_interval = obj.rules.spirallingExpenses.interval.cdata
    ruleset.se_pace = obj.rules.spirallingExpenses.pace.cdata

    print("Done loading rules")

    return ruleset


def get_all_teams(ruleset):
    path = get_data_path('teams/')
    teams = []
    for file in list(glob.glob(path + '/*.json')):
        name = file.split("/")[-1].split(".")[0]
        teams.append(get_team(name, ruleset))
    return teams


def get_team_by_id(team_id, ruleset):
    path = get_data_path('teams/')
    for file in list(glob.glob(path + '/*.json')):
        name = file.split("/")[-1].split(".")[0]
        team = get_team(name, ruleset)
        if team.team_id == team_id:
            return team
    return None


def get_team(name, ruleset):
    path = get_data_path('teams/' + name + '.json')
    f = open(path)
    str = f.read()
    f.close()
    data = json.loads(str)
    coach = Coach(data['coach']['id'], data['coach']['name'])
    team = Team(data['id'], data['name'], data['race'], players=[], coach=coach, treasury=data['treasury'], apothecary=data['apothecary'], rerolls=data['rerolls'], ass_coaches=data['ass_coaches'], cheerleaders=data['cheerleaders'], fan_factor=data['fan_factor'])
    for p in data['players']:
        role = ruleset.get_position(p['position'], team.race)
        player = Player(player_id=p['id'], role=role, name=p['name'], nr=p['nr'], niggling=p['niggling'], extra_ma=p['extra_ma'], extra_st=p['extra_st'], extra_ag=p['extra_ag'], extra_av=p['extra_av'], mng=p['mng'], spp=p['spp'], team=team)
        for s in p['extra_skills']:
            player.extra_skills.append(parse_enum(Skill, s))
        team.players.append(player)
    return team


def get_arena(name):
    path = get_data_path('arenas/' + name)
    name = 'Unknown arena'
    dungeon = False
    board = []
    file = open(path, 'r')
    while True:
        line = file.readline()
        if not line:
            break
        row = []
        for c in line:
            if c not in arena_char_map.keys():
                if c in ['\n']:
                    continue
                file.close()
                raise Exception("Unknown tile type " + c)
            row.append(arena_char_map[c])
        board.append(np.array(row))
    file.close()
    return TwoPlayerArena(np.array(board))


def get_config(name):
    path = get_data_path('config/' + name)
    f = open(path)
    str = f.read()
    f.close()
    data = json.loads(str)
    config = Configuration()
    config.name = data['name']
    config.arena = data['arena']
    config.ruleset = data['ruleset']
    config.dungeon = data['dungeon']
    config.roster_size = data['roster_size']
    config.pitch_max = data['pitch_max']
    config.pitch_min = data['pitch_min']
    config.scrimmage_min = data['scrimmage_min']
    config.wing_max = data['wing_max']
    config.rounds = data['turns']
    config.kick_off_table = data['kick_off_table']
    config.fast_mode = data['fast_mode']
    return config

