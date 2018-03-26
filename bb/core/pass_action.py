from core import Procedure, Bounce, Catch, Turnover, Scatter, DeterminePassSuccess, Interception
from model import Outcome, OutcomeType, ActionType, DiceRoll, D6, PlayerState, Skill, WeatherType, Rules, PassDistance


class PassAction(Procedure):

    #          0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    success = [6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1]

    ready_to_catch = [PlayerState.READY, PlayerState.USED]

    def __init__(self, game, home, player_from, pos_from, player_to, pos_to, pass_distance):
        super().__init__(game)
        self.home = home
        self.player_from = player_from
        self.pos_from = pos_from
        self.player_to = player_to
        self.pos_to = pos_to
        self.pass_distance = pass_distance
        self.pass_roll = None
        self.reroll_used = False
        self.pass_used = False
        self.waiting_for_reroll = False
        self.waiting_for_pass = False
        self.fumble = False
        self.interception_tried = False

    def step(self, action):

        # Otherwise roll if player hasn't rolled
        if self.pass_roll is None:

            # Check for interception
            if not self.interception_tried:
                interceptors = self.game.state.field.interceptors(self.pos_from, self.pos_to, self.home)
                if len(interceptors) > 0:
                    Interception(self.game, not self.home, interceptors)
                    self.interception_tried = True
                    return False

            # Set modifiers
            modifiers = Rules.pass_modifiers[self.pass_distance]
            tackle_zones = self.game.state.field.in_tackle_zones(self.player_from.player_id)
            modifiers -= tackle_zones

            # Weather
            if self.game.state.weather == WeatherType.VERY_SUNNY:
                modifiers -= 1

            if self.player_from.has_skill(Skill.ACCURATE):
                modifiers += 1

            if self.player_from.has_skill(Skill.STRONG_ARM):
                if self.pass_distance == PassDistance.SHORT_PASS or self.pass_distance == PassDistance.LONG_PASS or \
                                self.pass_distance == PassDistance.LONG_BOMB:
                    modifiers += 1

            # Find success target
            target = Catch.success[self.player_from.get_ag()]

            # Roll
            roll = DiceRoll([D6], target=target)
            roll.modifiers = modifiers
            result = roll.get_sum()
            mod_result = result + roll.modifiers

            if result == 6 or (result != 1 and mod_result >= target):

                # Accurate pass
                self.game.report(Outcome(OutcomeType.ACCURATE_PASS, player_id=self.player_from.player_id, rolls=[roll]))
                Catch(self.game, self.home, self.player_from.player_id, self.pos_to, accurate=True)
                return True

            elif result == 1 or mod_result <= 1:

                # Fumble
                self.fumble = True
                self.game.report(Outcome(OutcomeType.FUMBLE, player_id=self.player_from.player_id, pos=self.pos_from, rolls=[roll]))

            else:

                # Inaccurate pass
                self.game.report(Outcome(OutcomeType.INACCURATE_PASS, player_id=self.player_from.player_id, pos=self.pos_from, rolls=[roll]))

            # Check if player has pass
            if self.player_from.has_skill(Skill.PASS) and not self.pass_used:
                self.pass_used = True
                self.waiting_for_pass = True
                return False

            # Check if reroll available
            if self.game.state.can_use_reroll(self.home) and not self.pass_used:
                self.waiting_for_reroll = True
                return False

            # Effect
            if self.fumble:
                Turnover(self.game, self.home)
                Bounce(self.game, self.home)
            else:
                DeterminePassSuccess(self.game, self.home)
                Scatter(self.game, self.home, is_pass=True)

            return True

        # If catch used
        if self.waiting_for_pass:
            if action.action_type == ActionType.USE_SKILL:
                self.pass_used = True
                self.pass_roll = None
                return self.step(None)
            elif self.fumble:
                Turnover(self.game, self.home)
                Bounce(self.game, self.home)
                return True

            DeterminePassSuccess(self.game, self.home)
            Scatter(self.game, self.home, is_pass=True)
            return True

        # If re-roll used
        if self.waiting_for_reroll:
            if action.action_type == ActionType.USE_REROLL:
                self.reroll_used = True
                self.game.state.use_reroll(self.home)
                self.pass_roll = None
                return self.step(None)
            elif self.fumble:
                Turnover(self.game, self.home)
                Bounce(self.game, self.home)
                return True

            DeterminePassSuccess(self.game, self.home)
            Scatter(self.game, self.home, is_pass=True)
            return True

        return True
