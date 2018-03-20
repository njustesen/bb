from procs.pregame import Pregame


class Game:

    def __init__(self, home, away, arena, state):
        self.home = home
        self.away = away
        self.arena = arena
        self.state = state
        self.procedure = []

    def init(self):
        self.procedure.append(Pregame())
        self.procedure.append(Half())
        self.procedure.append(Half())
        #self.procedure.append(Postgame())
