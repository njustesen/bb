

class Outcome:

    def __init__(self, outcome_type, x=-1, y=-1, player_id=-1, roll=None, team_home=None):
        self.outcome_type = outcome_type
        self.x = x
        self.y = y
        self.player_id = player_id
        self.roll = roll
        self.team_home = team_home
