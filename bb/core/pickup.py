from core import Procedure, Bounce
from model import Outcome, OutcomeType, ActionType, DiceRoll, D6, Skill, WeatherType


class Pickup(Procedure):

    #          0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    success = [6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1]

    def __init__(self, game, home, player_id, pos):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.pos = pos
        self.rolled = False
        self.reroll_used = False
        self.sure_hands_used = False
        self.waiting_for_reroll = False
        self.waiting_for_sure_hands = False

    def step(self, action):

        # Otherwise roll if player hasn't rolled
        if action is None and not self.rolled:

            # Set modifiers
            modifiers = 1

            player = self.game.get_player(self.player_id)
            tackle_zones = self.game.state.field.in_tackle_zones(self.player_id)
            if not player.has_skill(Skill.BIG_HAND):
                modifiers -= tackle_zones

            # Weather
            if self.game.state.weather == WeatherType.POURING_RAIN:
                if not player.has_skill(Skill.BIG_HAND):
                    modifiers -= 1

            # Extra arms
            if not player.has_skill(Skill.EXTRA_ARMS):
                modifiers += 1

            # Find success target
            target = Pickup.success[player.get_ag()]

            # Can player even handle the ball?
            if player.has_skill(Skill.NO_HANDS):
                Bounce(self.game, self.home)
                self.game.report(Outcome(OutcomeType.FAILED_PICKUP, player_id=self.player_id))

            # Roll
            roll = DiceRoll([D6], target=target)
            roll.modifiers = modifiers
            result = roll.get_sum()
            mod_result = result + modifiers
            if result == 6 or (result != 1 and mod_result >= target):
                self.game.report(Outcome(OutcomeType.SUCCESSFUL_PICKUP, player_id=self.player_id))
                return True
            else:
                # Check if sure hands
                player = self.game.get_player(self.player_id)
                if player.has_skill(Skill.SURE_HANDS) and not self.sure_hands_used:
                    self.sure_hands_used = True
                    self.waiting_for_sure_hands = True
                    self.game.report(Outcome(OutcomeType.FAILED_PICKUP, player_id=self.player_id, pos=self.pos, rolls=[roll]))
                    return False

                # Check if reroll available
                if self.game.state.can_use_reroll(self.home) and not self.sure_hands_used:
                    self.waiting_for_reroll = True
                    self.game.report(Outcome(OutcomeType.FAILED_PICKUP, player_id=self.player_id))
                    return False

                Scatter(self.game, self.home)
                self.game.report(Outcome(OutcomeType.FAILED_PICKUP, player_id=self.player_id))
                return True

        # If catch used
        if self.waiting_for_sure_hands:
            if action.action_type == ActionType.USE_SKILL:
                self.sure_hands_used = True
                self.rolled = False
                return self.step(None)
            else:
                Bounce(self.game, self.home)
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
                Bounce(self.game, self.home)
                self.game.report(Outcome(OutcomeType.DROP, player_id=self.player_id))

        return True