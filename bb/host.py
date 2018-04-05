import uuid


class Host:

    def __init__(self):
        self.games = {}

    def new_game(self, game):
        game_id = uuid.uuid1()
        self.games[game_id] = game
        return game_id

    def end_game(self, id):
        del self.games[id]

    def get_game(self, id):
        return self.games[id]
