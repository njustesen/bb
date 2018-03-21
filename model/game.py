from procs.pregame import Pregame
from procs.half import Half


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

    def get_team(self, home):
        return self.home if home else self.away

    def get_player(self, player_id):
        home = self.home.get_player_by_id(player_id)
        if home is not None:
            return home
        away = self.away.get_player_by_id(player_id)
        return away

    def get_team_by_player_id(self, player_id):
        if self.home.has_player_by_id(player_id):
            return self.home
        return self.away

    def is_on_home_team(self, player_id):
        if self.home.has_player_by_id(player_id):
            return True
        return False

    def is_on_team(self, player_id, home):
        if self.home.has_player_by_id(player_id):
            return home
        return not home
