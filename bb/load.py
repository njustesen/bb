import os
import untangle
from bb.model import *


def parse_skill(skill_name):
    enum_name = skill_name.upper().replace(" ", "_").replace("-", "_")
    if enum_name not in Skill.__members__:
        raise Exception("Uknown skill name " + enum_name + " (orig: " + skill_name + ")")
    return Skill[enum_name]


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

    rosters = []
    for r in obj.rules.rosters.roster:
        print("Parsing " + str(r.name.cdata))
        roster = Roster(r.name.cdata, [], (int)(r.rerollValue.cdata), (bool)(r.apothecary.cdata), (bool)(r.stakes.cdata))
        for p in r.positions.position:
            position = Position(p.title.cdata, roster.name, (int)(p.ma.cdata), (int)(p.st.cdata), (int)(p.ag.cdata), (int)(p.av.cdata), [], p.cost.cdata, parse_sc(p.normal.cdata), parse_sc(p.double.cdata))
            if len(p.skills) == 0:
                continue
            for skill_name in p.skills.skill:
                position.skills.append(parse_skill(skill_name.cdata))
            roster.positions.append(position)
        rosters.append(roster)

if __name__ == "__main__":
    file_dir = os.path.dirname(os.path.realpath('__file__'))
    filename = os.path.join(file_dir, "../data/LRB5-Experimental.xml")
    filename = os.path.abspath(os.path.realpath(filename))
    load_rules(filename)
