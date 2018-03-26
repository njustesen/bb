
class Coach:

    def __init__(self, coach_id, name):
        self.coach_id = coach_id
        self.name = name


class Roster:

    def __init__(self, name, positions, reroll_cost, apothecary, stakes):
        self.name = name
        self.positions = positions
        self.reroll_cost = reroll_cost
        self.apothecary = apothecary
        self.stakes = stakes


class Team:

    def __init__(self, team_id, name, roster, coach, players=[], treasury=0, apothecary=False, rerolls=0, ass_coaches=0,
                 cheerleaders=0):
        self.team_id = team_id
        self.name = name
        self.coach = coach
        self.roster = roster
        self.players = players
        self.treasury = treasury
        self.apothecary = apothecary
        self.rerolls = rerolls
        self.ass_coaches = ass_coaches
        self.cheerleaders = cheerleaders

        self.players_by_id = {}
        for player in self.players:
            self.players_by_id[player.id] = player

    def get_player_by_id(self, player_id):
        return self.players_by_id[player_id]

    def has_player_by_id(self, player_id):
        return player_id in self.players_by_id

    def get_player_ids(self):
        return [player.player_id for player in self.players]
