from bb.core.util import *
import pickle
import glob


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

    def save_game(self, game_id):
        game = self.get_game(game_id)
        filename = os.path.join(get_data_path("saves/"), game.game_id+".ffai")
        print("Saving game")
        pickle.dump(game, open(filename, "wb"))
        print("Game saved")

    def load_game(self, filename):
        print("Loading game")
        game = pickle.load(open(filename, "rb"))
        print("Game laoded")
        return game

    def get_saved_games(self):
        return glob.glob(get_data_path("saves/*"))
