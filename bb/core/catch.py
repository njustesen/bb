# from . import procedure, Skill, PlayerState, Outcome, OutcomeType, WeatherType, DiceRoll, D6, Turnover, ActionType
from core.procedure import *
from core.

class Catch(Procedure):

    #          0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    success = [6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1]

    ready_to_catch = [PlayerState.READY, PlayerState.USED]

    def __init__(self, game, home, player_id, pos, accurate=False, interception=False):
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
        self.interception = interception

    def step(self, action):

        # Otherwise roll if player hasn't rolled
        if action is None and not self.rolled:

            # Can player even catch ball?
            player = self.game.get_player(self.player_id)
            if player.has_skill(Skill.NO_HANDS) or self.game.state.get_player_state(self.player_id) not in Catch.ready_to_catch:
                Bounce(self.game, self.home)
                self.game.report(Outcome(OutcomeType.DROP, player_id=self.player_id))

            # Set modifiers
            modifiers = 1 if self.accurate else 0
            modifiers = -2 if self.interception else modifiers
            if self.interception and player.has_skill(Skill.LONG_LEGS):
                modifiers += 1

            tackle_zones = self.game.state.field.in_tackle_zones(self.player_id)
            modifiers -= tackle_zones

            # Weather
            if self.game.state.weather == WeatherType.POURING_RAIN:
                modifiers -= 1

            if player.has_skill(Skill.EXTRA_ARMS):
                modifiers += 1

            # Find success target
            target = Catch.success[player.get_ag()]

            # Roll
            roll = DiceRoll([D6], target=target)
            roll.modifiers = modifiers
            result = roll.get_sum()
            mod_result = result + roll.modifiers
            if result == 6 or (result != 1 and mod_result >= target):
                if self.interception:
                    self.game.report(m.Outcome(m.OutcomeType.INTERCEPTION, player_id=self.player_id))
                    Turnover(self.game, not self.home)
                else:
                    self.game.report(Outcome(OutcomeType.CATCH, player_id=self.player_id))
                return True
            else:
                # Check if catch
                player = self.game.get_player(self.player_id)
                if player.has_skill(Skill.CATCH) and not self.catch_used:
                    self.catch_used = True
                    self.waiting_for_catch = True
                    self.game.report(Outcome(m.OutcomeType.CATCH_FAILED, player_id=self.player_id, pos=self.pos, rolls=[roll]))
                    return False

                # Check if reroll available
                if self.game.state.can_use_reroll(self.home) and not self.catch_used:
                    self.waiting_for_reroll = True
                    self.game.report(Outcome(OutcomeType.CATCH_FAILED, player_id=self.player_id))
                    return False

                c.Bounce(self.game, self.home)
                self.game.report(Outcome(OutcomeType.CATCH_FAILED, player_id=self.player_id))
                return True

        # If catch used
        if self.waiting_for_catch:
            if action.action_type == ActionType.USE_SKILL:
                self.catch_used = True
                self.rolled = False
                return self.step(None)
            else:
                c.Bounce(self.game, self.home)
                self.game.report(Outcome(OutcomeType.CATCH_FAILED, player_id=self.player_id))
                return True

        # If re-roll used
        if self.waiting_for_reroll:
            if action.action_type == ActionType.USE_REROLL:
                self.reroll_used = True
                self.game.state.use_reroll(self.home)
                self.rolled = False
                return self.step(None)
            else:
                c.Bounce(self.game, self.home)
                self.game.report(Outcome(OutcomeType.CATCH_FAILED, player_id=self.player_id))

        return True
