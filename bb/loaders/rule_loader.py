import os
import untangle
from model import Roster, Position, Skill, SkillCategory


def parse_skill(skill_name):
    enum_name = skill_name.upper().replace(" ", "_")
    if enum_name not in Skill:
        raise Exception("Uknown skill name " + enum_name + " (orig: " + skill_name + ")")
    return Skill[enum_name]


def parse_sc(sc):

    parsed = []
    for cat in sc.split(""):
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
    for r in obj.rules.rosters:
        roster = Roster(r.name, [], r.rerollValue, r.apothecary, r.stakes)
        for p in r.positions:
            position = Position(p.name, roster.name, p.ma, p.st, p.ag, p.av, [], p.cost, parse_sc(p.normal), parse_sc(p.double))
            for skill_name in r.skills:
                position.skills.append(parse_skill(skill_name))
            roster.positions.append(position)
        rosters.append(roster)

file_dir = os.path.dirname(os.path.realpath('__file__'))
filename = os.path.join(file_dir, "../rulesets/LRB5-Experimental.xml")
filename = os.path.abspath(os.path.realpath(filename))
load_rules(filename)
