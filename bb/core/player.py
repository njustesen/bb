from enum import Enum


class PlayerState(Enum):
    READY = 1
    USED = 2
    DOWN_READY = 3
    DOWN_USED = 4
    STUNNED = 5
    KOD = 6
    BH = 7
    MNG = 8
    DEAD = 9
    BONE_HEADED = 10
    HYPNOTIZED = 11
    REALLY_STUPID = 12
    HEATED = 13
    EJECTED = 14


class Position:

    def __init__(self, name, race, ma, st, ag, av, skills, cost, feeder, n_skill_sets=[], d_skill_sets=[]):
        self.name = name
        self.race = race
        self.ma = ma
        self.st = st
        self.ag = ag
        self.av = av
        self.skills = skills
        self.cost = cost
        self.feeder = feeder
        self.n_skill_sets = n_skill_sets
        self.d_skill_sets = d_skill_sets


class Player:

    def __init__(self, player_id, position, name, nr, extra_skills=[], extra_ma=0, extra_st=0, extra_ag=0, extra_av=0):
        self.player_id = player_id
        self.position = position
        self.name = name
        self.nr = nr
        self.extra_skills = extra_skills
        self.extra_ma = extra_ma
        self.extra_st = extra_st
        self.extra_ag = extra_ag
        self.extra_av = extra_av

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