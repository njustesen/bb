from core import Procedure
from model import Outcome, OutcomeType, ActionType, WeatherType, PlayerState
from exception import IllegalActionExcpetion


class ClearBoard(Procedure):

    def __init__(self, game):
        super().__init__(game)

    def step(self, action):
        for team in [True, False]:
            for player_id in self.game.get_team(team).get_player_ids():
                # If player not in reserves. move it to it
                if self.game.field.get_player_position(player_id) is not None:
                    if self.game.state.weather == WeatherType.SWELTERING_HEAT:
                        self.game.state.set_player_state(player_id, team, PlayerState.HEATED)
                    self.game.state.field.remove(player_id)
                    self.game.state.get_dugout(team).reserves.append(player_id)

        return True


class Setup(Procedure):

    def __init__(self, game, home, reorganize=False):
        super().__init__(game)
        self.home = home
        self.reorganize = reorganize

    def step(self, action):

        if action.action_type == ActionType.PLACE_PLAYER:
            if self.game.arena.is_team_side(action.pos_to, self.home):
                if action.pos_from is None:  # From reserves
                    if self.reorganize:
                        raise IllegalActionExcpetion("You cannot move players from the reserves when reorganizing the defense")
                    self.game.state.get_dugout(self.home).remove(action.player_from_id)
                elif action.pos_to is None:  # To reserves
                    if self.reorganize:
                        raise IllegalActionExcpetion("You cannot move players to the reserves when reorganizing the defense")
                    self.game.state.field.remove(action.player_from_id)
                    self.game.state.get_dugout(self.home).add_to_reserves(action.player_from_id)
                else:
                    self.game.state.field.swap(action.pos_from, action.pos_to)
                self.game.report(Outcome(OutcomeType.PLAYER_PLACED, pos=action.pos_to, player_id=action.player_from_id))
                return False
            raise IllegalActionExcpetion("You can only place players on your own side")
        elif action.action_type == ActionType.END_SETUP:
            if not self.game.state.field.is_setup_legal(self.home):
                self.game.report(Outcome(OutcomeType.ILLEGAL_SETUP_NUM, team_home=self.home))
                return False
            elif not self.game.state.field.is_setup_legal_scrimmage(self.home):
                self.game.report(Outcome(OutcomeType.ILLEGAL_SETUP_SCRIMMAGE, team_home=self.home))
                return False
            elif not self.game.state.field.is_setup_legal_wings(self.home):
                self.game.report(Outcome(OutcomeType.ILLEGAL_SETUP_WINGS, team_home=self.home))
                return False
            self.game.report(Outcome(OutcomeType.SETUP_DONE, team_home=self.home))
            return True
