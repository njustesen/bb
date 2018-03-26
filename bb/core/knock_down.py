from core import Procedure, Turnover
from model import Outcome, OutcomeType, PlayerState, Bounce


class KnockDown(Procedure):

    def __init__(self, game, home, player_id, armor_roll=True, injury_roll=True, modifiers=0, opp_player_id=None, in_crowd=False, both_down=False, modifiers_opp=0, turnover=False):
        super().__init__(game)
        self.home = home  # owner of player_id
        self.player_id = player_id
        self.armor_roll = armor_roll
        self.injury_roll = injury_roll
        self.modifiers = modifiers
        self.modifiers_opp = modifiers_opp
        self.opp_player_id = opp_player_id
        self.in_crowd = in_crowd
        self.both_down = both_down
        self.turnover = turnover

    def step(self, action):

        # Knock down player
        self.game.state.get_team(self.home).player_states[self.player_id] = PlayerState.DOWN
        self.game.report(OutcomeType.KNOCKED_DOWN, player_id=self.player_id, opp_player_id=self.opp_player_id)
        if self.both_down:
            self.game.state.get_team(not self.home).player_states[self.opp_player_id] = PlayerState.DOWN
            self.game.report(OutcomeType.KNOCKED_DOWN, player_id=self.opp_player_id, opp_player_id=self.player_id)

        # Turnover
        if self.turnover:
            Turnover(self.game, self.home)

        # Check fumble
        pos = self.game.state.field.get_player_position(self.player_id)
        if self.game.state.ball_at(pos):
            Bounce(self.game, self.home)
            self.game.report(Outcome(OutcomeType.FUMBLE, player_id=self.player_id, opp_player_id=self.opp_player_id))

        if self.both_down:
            pos = self.game.state.field.get_player_position(self.opp_player_id)
            if self.game.state.ball_at(pos):
                Bounce(self.game, not self.home)
                self.game.report(Outcome(OutcomeType.FUMBLE, player_id=self.opp_player_id, opp_player_id=self.player_id))

        # If armor roll should be made. Injury is also nested in armor.
        if self.injury_roll and not self.armor_roll:
            Injury(self.game, self.home, self.player_id, opp_player_id=self.opp_player_id if not self.in_crowd else None)
        elif self.armor_roll:
            Armor(self.game, not self.home, self.player_id, modifiers=self.modifiers, opp_player_id=self.player_id)

        if self.both_down:
            if self.injury_roll and not self.armor_roll:
                Injury(self.game, self.home, self.opp_player_id, opp_player_id=self.player_id if not self.in_crowd else None)
            elif self.armor_roll:
                Armor(self.game, not self.home, self.opp_player_id, modifiers=self.modifiers, opp_player_id=self.player_id)

        return True
