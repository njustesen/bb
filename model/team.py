

class Team:

    def __init__(self, id, name, race, coach, players=[], treasury=0, apothecary=False, rerolls=0, ass_coaches=0, cheerleaders=0):
        self.id = id
        self.race = race
        self.players = players
        self.treasury = treasury
        self.apothecary = apothecary
        self.rerolls = rerolls
        self.ass_coaches = ass_coaches
        self.cheerleaders = cheerleaders

        self.players_by_id = {}
        for player in self.players:
            self.players_by_id[player.id] = player

    def get_player_by_id(self, id):
        return self.players_by_id[id]

    def has_player_by_id(self, id):
        return id in self.players_by_id

    def get_player_ids(self):
        return [player.id for player in self.players]
