from procs.procedure import Procedure
from model.action import Action, ActionType
from model.outcome import Outcome, OutcomeType
import numpy as np
from model.dice import *
from model.player import *


class Scatter(Procedure):

    def __init__(self, game, home, kick=False):
        self.game = game
        self.home = home  # Having the turn
        self.kick = kick
        super().__init__()

    def step(self, action):
        roll_scatter = DiceRoll([D8])
        if self.kick:
            roll_distance = DiceRoll([D6])

        x = 0
        y = 0
        if roll_scatter.get_sum() in [1, 4, 6]:
            x = -1
        if roll_scatter.get_sum() in [3, 5, 9]:
            x = 1
        if roll_scatter.get_sum() in [1, 2, 3]:
            y = -1
        if roll_scatter.get_sum() in [6, 7, 8]:
            y = 1

        distance = 1 if not self.kick else roll_distance.get_sum()

        for i in range(distance):
            self.game.state.field.ball_position[0] += x
            self.game.state.field.ball_position[1] += y
            if self.kick:
                if self.game.state.field.is_ball_out() or \
                        self.game.arena.is_team_side(self.game.state.field.ball_position, not self.home):
                    return Outcome(OutcomeType.KICK_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                   team_home=self.home, rolls=[roll_scatter, roll_distance]), True
            else:
                if self.game.state.field.is_ball_out():
                    # TODO: Throw in
                # TODO: Land on other player

        if self.kick:
            return Outcome(OutcomeType.KICK_IN_BOUNDS, pos=self.game.state.field.ball_position, team_home=self.home), True
        else:
            return Outcome(OutcomeType.BALL_HIT_GROUND, pos=self.game.state.field.ball_position, team_home=self.home), True


class Catch(Procedure):

    #          0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    success = [6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1]

    def __init__(self, game, home, player_id, pos, accurate=False):
        self.game = game
        self.home = home
        self.player_id = player_id
        self.pos = pos
        self.accurate = accurate
        self.procedures = []
        self.rolled = False
        self.reroll_used = False
        self.catch_used = False
        self.waiting_for_reroll = False
        self.waiting_for_catch = False
        self.game.state.move_ball(self.pos)
        super().__init__()

    def step(self, action):

        # Check if nested procedures
        if len(self.procedures) > 0:
            outcome, terminal = self.procedures[0].step(action)
            if outcome.terminal:
                self.procedures.pop()
                return outcome, True
            return outcome, False

        # Otherwise roll if player hasn't
        if action is None and not self.rolled:

            # Set modifiers
            modifiers = 1 if self.accurate else 0
            tackle_zones = self.game.state.field.in_tackle_zones(self.player_id)
            modifiers -= tackle_zones

            # Find success target
            player = self.game.get_player(self.player_id)
            mod_ag = max(0, min(player.get_ag() + modifiers, 10))
            target = Catch.success[mod_ag]

            # Roll
            roll = DiceRoll([D6], target=target)
            if roll.get_sum() >= target:
                return Outcome(OutcomeType.CATCH, player_id=self.player_id), True
            else:
                # Check if catch
                player = self.game.get_player(self.player_id)
                if player.has_skill(Skill.SURE_FEET) and not self.catch_used:
                    self.catch_used = True
                    self.awaiting_catch = True
                    return Outcome(OutcomeType.DROP, player_id=self.player_id, pos=self.pos, rolls=[roll]), False

                # Check if reroll available
                if self.game.state.can_use_reroll(self.home) and not self.catch_used:
                    self.awaiting_reroll = True
                    return Outcome(OutcomeType.DROP, player_id=self.player_id), False

                self.procedures.insert(0, Scatter(self.game, self.home))
                return Outcome(OutcomeType.DROP, player_id=self.player_id), False

        # If catch used
        if self.awaiting_catch:
            if action.action_type == ActionType.USE_SKILL:
                self.catch_used = True
                self.rolled = False
                self.step(None)
            else:
                self.procedures.insert(0, Scatter(self.game, self.home))
                return Outcome(OutcomeType.DROP, player_id=self.player_id), False

        # If re-roll used
        if self.awaiting_reroll:
            if action.action_type == ActionType.USE_REROLL:
                self.reroll_used = True
                self.game.state.use_reroll(self.home)
                self.rolled = False
                self.step(None)
            else:
                self.procedures.insert(0, Scatter(self.game, self.home))
                return Outcome(OutcomeType.DROP, player_id=self.player_id), False