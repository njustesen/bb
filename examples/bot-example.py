from bb.core.model import *
from bb.core.game import *
from bb.core.api import *
import numpy as np
import time


class MyRandomBot(Agent):

    def __init__(self, name):
        super().__init__(name)
        self.my_team = None
        self.actions_taken = 0

    def new_game(self, game, team):
        self.my_team = team
        self.actions_taken = 0

    def act(self, game):
        while True:
            action_choice = np.random.choice(game.state.available_actions)
            if action_choice.action_type != ActionType.PLACE_PLAYER:
                break
        pos = np.random.choice(action_choice.positions) if len(action_choice.positions) > 0 else None
        player = np.random.choice(action_choice.players) if len(action_choice.players) > 0 else None
        action = Action(action_choice.action_type, pos=pos, player=player)
        self.actions_taken += 1
        return action

    def end_game(self, game):
        winner = game.get_winner()
        if winner is None:
            print("It's a draw")
        elif winner == self.my_team:
            print("I ({}) won".format(self.name))
        else:
            print("I ({}) lost".format(self.name))
        print("I took", self.actions_taken, "actions")


if __name__ == "__main__":

    # Avoid loading config and rules every time
    config = get_config("ff.json")
    ruleset = get_rule_set(config.ruleset)
    arena = get_arena(config.arena)
    home = get_team_by_id("human-team-1", ruleset)
    away = get_team_by_id("human-team-2", ruleset)

    for i in range(100):
        away_agent = MyRandomBot("Random Bot 1")
        home_agent = MyRandomBot("Random Bot 2")
        game = Game(i, deepcopy(home), deepcopy(away), home_agent, away_agent, config, arena=arena, ruleset=ruleset)
        game.config.fast_mode = True

        print("Starting game", i)
        start = time.time()
        game.init()
        game.run()
        end = time.time()
        print(end - start)
