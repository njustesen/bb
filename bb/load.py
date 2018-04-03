import os
import untangle
from bb.model import *


def parse_enum(enum_class, skill_name):
    enum_name = skill_name.upper().replace(" ", "_").replace("-", "_")
    if enum_name not in enum_class.__members__:
        raise Exception("Uknown skill name " + enum_name + " (orig: " + skill_name + ")")
    return enum_class[enum_name]


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


def load_rules(path):

    obj = untangle.parse(path)

    ruleset = RuleSet(path.split("/")[-1])

    print("Parsing rosters")

    for r in obj.rules.rosters.roster:
        print("-- Parsing " + str(r.name.cdata))
        roster = Roster(r.name.cdata, [], (int)(r.rerollValue.cdata), (bool)(r.apothecary.cdata), (bool)(r.stakes.cdata))
        for p in r.positions.position:
            position = Position(p.title.cdata, [roster.name], (int)(p.ma.cdata), (int)(p.st.cdata), (int)(p.ag.cdata), (int)(p.av.cdata), [], p.cost.cdata, parse_sc(p.normal.cdata), parse_sc(p.double.cdata))
            if len(p.skills) == 0:
                continue
            for skill_name in p.skills.skill:
                position.skills.append(parse_enum(Skill, skill_name.cdata))
            roster.positions.append(position)
        ruleset.rosters.append(roster)

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

'''
if __name__ == "__main__":
    file_dir = os.path.dirname(os.path.realpath('__file__'))
    filename = os.path.join(file_dir, "../data/LRB5-Experimental.xml")
    filename = os.path.abspath(os.path.realpath(filename))
    load_rules(filename)
'''