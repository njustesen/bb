

class Position:

    def __init__(self, name, race, ma, st, ag, av, skills, cost, n_skills = [], d_skills = []):
        self.name = name
        self.race = race
        self.ma = ma
        self.st = st
        self.ag = ag
        self.av = av
        self.skills = skills
        self.cost = cost
        self.n_skills = n_skills
        self.d_skills = d_skills