from enum import Enum


class PlayerState(Enum):
    READY = 1
    USED = 2
    ACTIVE = 3
    DOWN = 4
    STUNNED = 5
    KOD = 6
    BH = 7
    DEAD = 8


class Player:

    def __init__(self, id, position, name, nr, extra_skills=[], extra_ma=0, extra_st=0, extra_ag=0, extra_av=0):
        self.id = id
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
