from core import Procedure, Catch
from model import ActionType
from exception import IllegalActionExcpetion


class Interception(Procedure):

    def __init__(self, game, home, interceptors):
        super().__init__(game)
        self.home = home
        self.interceptors = interceptors

    def step(self, action):

        if action.action_type == ActionType.INTERCEPTION:

            if action.player_from_id not in self.interceptors:
                raise IllegalActionExcpetion("The selected player cannot intercept")

            pos = self.game.state.field.get_player_position(action.player_from_id)
            Catch(self.game, self.home, action.player_from_id, pos, interception=True)

        return True
