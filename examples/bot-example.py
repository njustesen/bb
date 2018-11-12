from bb.core.model import *
from bb.core.game import *
import np

class MyBot(Agent):

    def __init__(self):
        super().__init__("MyBot")
        self.my_team = None

    def new_game(self, game, team):
        self.my_team = team

    def act(self, game):
        action_choice = np.random.choice(game.state.available_actions)
        action = Action(action_choice.action_type,
                        pos_from=pos,
                        pos_to=pos,
                        player_from_id=player_id,
                        player_to_id=player_id,
                        idx=0,
                        team_id=self.my_team.team_id)