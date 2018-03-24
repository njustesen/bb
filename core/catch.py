from core import Procedure
from model import Outcome, OutcomeType, ActionType, DiceRoll, D3, D6, D8, PlayerState, Skill, WeatherType


class ThrowIn(Procedure):

    def __init__(self, game, home, pos):
        super().__init__(game)
        self.home = home  # With turn
        self.pos = pos

    def step(self, action):

        # Roll
        roll_scatter = DiceRoll([D3()])
        roll_distance = DiceRoll([D6(), D6()])

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
                ThrowIn(self.game, self.home, self.game.state.field.ball_position)
                self.game.report(Outcome(OutcomeType.BALL_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                         team_home=self.home, rolls=[roll_scatter, roll_distance]))
            else:

                # On player -> Catch
                player_id = self.game.field.get_player_id_at(self.game.state.field.ball_position)
                if player_id is not None:
                    Catch(self.game, self.home, player_id, self.game.state.field.ball_position)
                    self.game.report(Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.game.state.field.ball_position,
                                             player_id=player_id, rolls=[roll_scatter]))

                # On ground
                else:
                    self.game.report(Outcome(OutcomeType.BALL_ON_GROUND, pos=self.game.state.field.ball_position,
                                             team_home=self.home))

        return True


class Bounce(Procedure):

    def __init__(self, game, home, kick=False):
        super().__init__(game)
        self.home = home  # With turn
        self.kick = kick

    def step(self, action):

        # Roll
        roll_scatter = DiceRoll([D8()])

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
                self.game.report(Outcome(OutcomeType.TOUCHBACK, pos=self.game.state.field.ball_position,
                                         team_home=self.home, rolls=[roll_scatter]))
        else:
            # Out of bounds
            if self.game.state.field.is_ball_out():
                ThrowIn(self.game, self.home, self.game.state.field.ball_position)
                self.game.report(Outcome(OutcomeType.BALL_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                         team_home=self.home, rolls=[roll_scatter]))
            # On player -> Catch
            player_id = self.game.field.get_player_id_at(self.game.state.field.ball_position)
            if player_id is not None:
                Catch(self.game, self.home, player_id, self.game.state.field.ball_position)
                self.game.report(Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.game.state.field.ball_position,
                                         player_id=player_id, rolls=[roll_scatter]))

        self.game.report(Outcome(OutcomeType.BALL_ON_GROUND, pos=self.game.state.field.ball_position, team_home=self.home))
        return True


class Scatter(Procedure):

    def __init__(self, game, home, kick=False):
        super().__init__(game)
        self.home = home  # Having the turn
        self.kick = kick

    def step(self, action):

        # Roll
        roll_scatter = DiceRoll([D8()])
        if self.kick:
            roll_distance = DiceRoll([D6()])

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
                    # Touchback will be enforced in after kick-off table when ball lands
                    self.game.report(Outcome(OutcomeType.KICK_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                   team_home=self.home, rolls=[roll_scatter, roll_distance]))
            else:
                # Throw in
                if self.game.state.field.is_ball_out():
                    # Move ball back
                    self.game.state.field.ball_position[0] -= x
                    self.game.state.field.ball_position[1] -= y
                    ThrowIn(self.game, self.home, self.game.state.field.ball_position)
                    self.game.report(Outcome(OutcomeType.BALL_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                   team_home=self.home, rolls=[roll_scatter]))

                # On player -> Catch
                player_id = self.game.field.get_player_id_at(self.game.state.field.ball_position)
                if player_id is not None:
                    Catch(self.game, self.home, player_id, self.game.state.field.ball_position)
                    self.game.report(Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.game.state.field.ball_position,
                                   player_id=player_id, rolls=[roll_scatter]))

        if self.kick:
            self.game.report(Outcome(OutcomeType.KICK_IN_BOUNDS, pos=self.game.state.field.ball_position, team_home=self.home))
        else:
            self.game.report(Outcome(OutcomeType.BALL_HIT_GROUND, pos=self.game.state.field.ball_position, team_home=self.home))

        return True


class Catch(Procedure):

    #          0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    success = [6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1]

    ready_to_catch = [PlayerState.READY, PlayerState.USED]

    def __init__(self, game, home, player_id, pos, accurate=False):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.pos = pos
        self.accurate = accurate
        self.rolled = False
        self.reroll_used = False
        self.catch_used = False
        self.waiting_for_reroll = False
        self.waiting_for_catch = False
        self.game.state.move_ball(self.pos)

    def step(self, action):

        # Otherwise roll if player hasn't rolled
        if action is None and not self.rolled:

            # Set modifiers
            modifiers = 1 if self.accurate else 0
            tackle_zones = self.game.state.field.in_tackle_zones(self.player_id)
            modifiers -= tackle_zones

            # Weather
            if self.game.state.weather == WeatherType.POURING_RAIN:
                modifiers -= 1

            # Find success target
            player = self.game.get_player(self.player_id)
            mod_ag = max(0, min(player.get_ag() + modifiers, 10))
            target = Catch.success[mod_ag]

            # Can player even catch ball?
            if player.has_skill(Skill.NO_HANDS) or self.game.state.get_player_state(self.player_id) not in Catch.ready_to_catch:
                Scatter(self.game, self.home)
                self.game.report(Outcome(OutcomeType.DROP, player_id=self.player_id))

            # Roll
            roll = DiceRoll([D6], target=target)
            if roll.get_sum() >= target:
                self.game.report(Outcome(OutcomeType.CATCH, player_id=self.player_id))
                return True
            else:
                # Check if catch
                player = self.game.get_player(self.player_id)
                if player.has_skill(Skill.SURE_FEET) and not self.catch_used:
                    self.catch_used = True
                    self.waiting_for_catch = True
                    self.game.report(Outcome(OutcomeType.DROP, player_id=self.player_id, pos=self.pos, rolls=[roll]))
                    return False

                # Check if reroll available
                if self.game.state.can_use_reroll(self.home) and not self.catch_used:
                    self.waiting_for_reroll = True
                    self.game.report(Outcome(OutcomeType.DROP, player_id=self.player_id))
                    return False

                Scatter(self.game, self.home)
                self.game.report(Outcome(OutcomeType.DROP, player_id=self.player_id))
                return True

        # If catch used
        if self.waiting_for_catch:
            if action.action_type == ActionType.USE_SKILL:
                self.catch_used = True
                self.rolled = False
                return self.step(None)
            else:
                Scatter(self.game, self.home)
                self.game.report(Outcome(OutcomeType.DROP, player_id=self.player_id))
                return True

        # If re-roll used
        if self.waiting_for_reroll:
            if action.action_type == ActionType.USE_REROLL:
                self.reroll_used = True
                self.game.state.use_reroll(self.home)
                self.rolled = False
                return self.step(None)
            else:
                Scatter(self.game, self.home)
                self.game.report(Outcome(OutcomeType.DROP, player_id=self.player_id))

        return True