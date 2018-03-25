from core import Procedure, KnockDown
from model import ActionType, Skill, Outcome, OutcomeType
from exception import IllegalActionExcpetion


class FollowUp(Procedure):

    def __init__(self, game, home, player_from, pos_to, chain=False, optional=True):
        super().__init__(game)
        self.home = home  # With turn
        self.player_from = player_from
        self.pos_to = pos_to
        self.optional = optional

    def step(self, action):

        if not self.optional or self.player_from.has_skill(Skill.FRENZY) or action.action_type == ActionType.FOLLOW_UP:
            self.game.field.move(self.player_from, self.pos_to)

        return True


class Push(Procedure):

    def __init__(self, game, home, player_from, player_to, knock_down=False, blitz=False, chain=False):
        super().__init__(game)
        self.home = home  # With turn
        self.player_from = player_from
        self.player_to = player_to
        self.knock_down = knock_down
        self.blitz = blitz
        self.waiting_stand_firm = False
        self.stand_firm_used = False
        self.chain = chain
        self.waiting_for_move = False
        self.player_at = None
        self.push_to = None

    def step(self, action):

        # Use stand firm
        if self.waiting_stand_firm:
            if action.action_type == ActionType.USE_STAND_FIRM:
                if self.game.get_home_by_player_id(self.player_to) != action.home:
                    raise IllegalActionExcpetion("Must be the owner of the player to use the stand firm skill.")
                return True
            else:
                self.waiting_stand_firm = False
                self.stand_firm_used = True

        # Stand firm
        if self.player_to.has_skill(Skill.STAND_FIRM) and not self.stand_firm_used:
            if not (self.blitz and self.player_from.has_skill(Skill.JUGGERNAUT)):
                self.waiting_stand_firm = True
                return False

        # Find push squares
        pos_from = self.game.state.field.get_player_position(self.player_from.player_id)
        pos_to = self.game.state.field.get_player_position(self.player_from.player_id)
        squares = self.game.field.push_squares(pos_from, pos_to)

        if action.action_type == ActionType.SELECT_SQUARE:
            if action.home == self.home and self.player_to.has_skill(Skill.SIDE_STEP):
                raise IllegalActionExcpetion("Player with side step must choose square")
            if action.away == self.home and not self.player_to.has_skill(Skill.SIDE_STEP):
                raise IllegalActionExcpetion("Blocking player must choose square")
            if action.pos_to not in squares:
                raise IllegalActionExcpetion("Illegal square")

            crowd = self.game.field.is_out_of_bounds(action.pos_to)

            # Report
            if crowd:
                self.game.report(Outcome(OutcomeType.PUSHED_INTO_CROWD, player_id=self.player_to))
            else:
                self.game.report(Outcome(OutcomeType.PUSHED, player_id=self.player_to, pos=action.pos_to))

            # Follow up
            if not crowd:
                FollowUp(self.game, self.home, self.player_to, action.pos_to, optional=not self.chain)

            # Knock down
            if self.knock_down or crowd:
                KnockDown(self.game, self.home, self.player_to, in_crowd=crowd)

            # Chain push
            player_id_at = self.game.field.get_player_id_at(action.pos_to)
            self.push_to = action.pos_to
            if player_id_at is not None:
                self.player_at = self.game.get_player(player_id_at)
                Push(self.game, self.player_to, self.player_at, action.pos_to, knock_down=False, chain=True)
                # Wait for chain to finish
                self.waiting_for_move = True
                return False
            else:
                # Otherwise, move pushed player
                if crowd:
                    self.game.field.remove(self.player_to)
                else:
                    self.game.field.move(self.player_to, self.push_to)
                return True

        # When push chain is over, move player
        if self.waiting_for_move:
            self.game.field.move(self.player_to, self.push_to)
            return True

        raise Exception("Unknown push sequence")
