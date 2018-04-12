

class Host:

    def __init__(self, ruleset):
        self.games = {}
        self.ruleset = ruleset

    def add_game(self, game):
        self.games[game.game_id] = game

    def end_game(self, id):
        del self.games[id]

    def get_game(self, id):
        return self.games[id]

    def get_games(self):
        return list(self.games.values())
