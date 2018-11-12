from bb.core.model import *
from bb.core.game import *
from bb.core.api import *
import numpy as np
import time

class MyRandomBot(Agent):

    def __init__(self, name):
        super().__init__(name)
        self.my_team = None

    def new_game(self, game, team):
        self.my_team = team

    def act(self, game):
        while True:
            action_choice = np.random.choice(game.state.available_actions)
            if action_choice.action_type != ActionType.PLACE_PLAYER:
                break
        pos = np.random.choice(action_choice.positions) if len(action_choice.positions) > 0 else None
        player = np.random.choice(action_choice.players) if len(action_choice.players) > 0 else None
        action = Action(action_choice.action_type, pos=pos, player=player)
        return action

    def end_game(self, game):
        winner = game.get_winner()
        if winner == self.my_team:
            print("I ({}) won".format(self.name))
        else:
            print("I ({}) lost".format(self.name))


if __name__ == "__main__":

    away_agent = MyRandomBot("Random Bot 1")
    home_agent = MyRandomBot("Random Bot 2")
    game = new_game(away_team_id="human-team-1",
                    home_team_id="human-team-2",
                    away_agent=away_agent,
                    home_agent=home_agent)
    game.config.fast_mode = True

    start = time.time()
    game.init()
    game.run()
    end = time.time()
    print(end - start)
