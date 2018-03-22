from procs.procedure import Procedure
from model.action import Action, ActionType
from model.outcome import Outcome, OutcomeType
import numpy as np
from model.dice import *
from model.player import *


class ThrowIn(Procedure):

    def __init__(self, game, home, pos):
        self.game = game
        self.home = home  # With turn
        self.pos = pos
        self.rolled = False
        self.procedures = []
        super().__init__()

    def step(self, action):

        # Check if nested procedures
        if len(self.procedures) > 0:
            outcome, terminal = self.procedures[0].step(action)
            if outcome.terminal:
                self.procedures.pop()
                if len(self.procedures) == 0:
                    return outcome, True
            return outcome, False

        if not self.rolled:

            # Roll
            roll_scatter = DiceRoll([D3()])
            roll_distance = DiceRoll([D6(), D6()])
            self.rolled = True

            # Scatter
            x = 0
            y = 0
            if self.pos[0] < 0:  # Above
                y = -1
            elif self.pos[0] > len(self.game.arena.board[0]):  # Below
                y = 1
            elif self.pos[1] < 0:  # Right
                x = 1
            elif self.pos[1] < len(self.game.arena.board[1]):  # Left
                x = -1

            if roll_scatter.get_sum() == 1:
                if x == 0:
                    x = -1
                elif y == 0:
                    y = 1
            if roll_scatter.get_sum() == 3:
                if x == 0:
                    x = 1
                elif y == 0:
                    y = -1

            for i in range(roll_distance.get_sum()):
                self.game.state.field.ball_position[0] += x
                self.game.state.field.ball_position[1] += y
                if self.game.state.field.is_ball_out():
                    # Move ball back
                    self.game.state.field.ball_position[0] -= x
                    self.game.state.field.ball_position[1] -= y
                    self.procedures.insert(0, ThrowIn(self.game, self.home, self.game.state.field.ball_position))
                    return Outcome(OutcomeType.BALL_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                   team_home=self.home, rolls=[roll_scatter, roll_distance]), False
                # On player -> Catch
                player_id = self.game.field.get_player_id_at(self.game.state.field.ball_position)
                if player_id is not None:
                    self.procedures.insert(0, Catch(self.game, self.home, player_id, self.game.state.field.ball_position))
                    return Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.game.state.field.ball_position,
                                   player_id=player_id, rolls=[roll_scatter]), False

            return Outcome(OutcomeType.BALL_ON_GROUND, pos=self.game.state.field.ball_position, team_home=self.home), True


class Bounce(Procedure):

    def __init__(self, game, home, kick=False):
        self.game = game
        self.home = home  # With turn
        self.kick = kick
        self.rolled = False
        self.procedures = []
        super().__init__()

    def step(self, action):

        # Check if nested procedures
        if len(self.procedures) > 0:
            outcome, terminal = self.procedures[0].step(action)
            if outcome.terminal:
                self.procedures.pop()
                if len(self.procedures) == 0:
                    return outcome, True
            return outcome, False

        # Roll
        if not self.rolled:
            # Roll
            roll_scatter = DiceRoll([D8()])
            self.rolled = True

            # Bounce
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

            self.game.state.field.ball_position[0] += x
            self.game.state.field.ball_position[1] += y
            if self.kick:
                # Kick - out of bounds
                if self.game.state.field.is_ball_out() or \
                        self.game.arena.is_team_side(self.game.state.field.ball_position, not self.home):
                    return Outcome(OutcomeType.TOUCHBACK, pos=self.game.state.field.ball_position, team_home=self.home,
                                   rolls=[roll_scatter]), True
            else:
                # Out of bounds
                if self.game.state.field.is_ball_out():
                    self.procedures.insert(0, ThrowIn(self.game, self.home, self.game.state.field.ball_position))
                    return Outcome(OutcomeType.BALL_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                   team_home=self.home, rolls=[roll_scatter]), False
                # On player -> Catch
                player_id = self.game.field.get_player_id_at(self.game.state.field.ball_position)
                if player_id is not None:
                    self.procedures.insert(0, Catch(self.game, self.home, player_id, self.game.state.field.ball_position))
                    return Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.game.state.field.ball_position,
                                   player_id=player_id, rolls=[roll_scatter]), False

            return Outcome(OutcomeType.BALL_ON_GROUND, pos=self.game.state.field.ball_position, team_home=self.home), True


class Scatter(Procedure):

    def __init__(self, game, home, kick=False):
        self.game = game
        self.home = home  # Having the turn
        self.kick = kick
        self.rolled = False
        self.procedures = []
        super().__init__()

    def step(self, action):

        # Check if nested procedures
        if len(self.procedures) > 0:
            outcome, terminal = self.procedures[0].step(action)
            if outcome.terminal:
                self.procedures.pop()
                if len(self.procedures) == 0:
                    return outcome, True
            return outcome, False

        # Roll
        if not self.rolled:
            roll_scatter = DiceRoll([D8()])
            if self.kick:
                roll_distance = DiceRoll([D6()])
            self.rolled = True

            # Scatter
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
                # Move ball on square
                self.game.state.field.ball_position[0] += x
                self.game.state.field.ball_position[1] += y

                # Check out of bounds
                if self.kick:
                    if self.game.state.field.is_ball_out() or \
                            self.game.arena.is_team_side(self.game.state.field.ball_position, not self.home):
                        # Touchback will be enforced after kick-off table
                        return Outcome(OutcomeType.KICK_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                       team_home=self.home, rolls=[roll_scatter, roll_distance]), True
                else:
                    # Throw in
                    if self.game.state.field.is_ball_out():
                        # Move ball back
                        self.game.state.field.ball_position[0] -= x
                        self.game.state.field.ball_position[1] -= y
                        self.procedures.insert(0, ThrowIn(self.game, self.home, self.game.state.field.ball_position))
                        return Outcome(OutcomeType.BALL_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                       team_home=self.home, rolls=[roll_scatter]), False

                    # On player -> Catch
                    player_id = self.game.field.get_player_id_at(self.game.state.field.ball_position)
                    if player_id is not None:
                        self.procedures.insert(0, Catch(self.game, self.home, player_id, self.game.state.field.ball_position))
                        return Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.game.state.field.ball_position,
                                       player_id=player_id, rolls=[roll_scatter]), False

            if self.kick:
                return Outcome(OutcomeType.KICK_IN_BOUNDS, pos=self.game.state.field.ball_position, team_home=self.home), True
            else:
                return Outcome(OutcomeType.BALL_HIT_GROUND, pos=self.game.state.field.ball_position, team_home=self.home), True


class Catch(Procedure):

    #          0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    success = [6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1]

    ready_to_catch = [PlayerState.READY, PlayerState.USED]

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
                if len(self.procedures) == 0:
                    return outcome, True
            return outcome, False

        # Otherwise roll if player hasn't rolled
        if action is None and not self.rolled:

            # Set modifiers
            modifiers = 1 if self.accurate else 0
            tackle_zones = self.game.state.field.in_tackle_zones(self.player_id)
            modifiers -= tackle_zones

            # Find success target
            player = self.game.get_player(self.player_id)
            mod_ag = max(0, min(player.get_ag() + modifiers, 10))
            target = Catch.success[mod_ag]

            # Can player even catch ball?
            if player.has_skill(Skill.NO_HANDS) or self.game.state.get_player_state(self.player_id) not in Catch.ready_to_catch:
                self.procedures.insert(0, Scatter(self.game, self.home))
                return Outcome(OutcomeType.DROP, player_id=self.player_id), False

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