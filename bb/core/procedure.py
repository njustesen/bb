import numpy as np
from bb.core.model import *
from bb.core.table import *
from bb.core.exception import *


class Procedure:

    def __init__(self, game):
        self.game = game
        self.game.stack.push(self)
        self.done = False

    def step(self, action):
        pass

    def available_actions(self):
        pass


class Apothecary(Procedure):

    def __init__(self, game, player, roll, outcome, inflictor, casualty=None, effect=None):
        super().__init__(game)
        self.game = game
        self.player = player
        self.inflictor = inflictor
        self.waiting_apothecary = False
        self.roll_first = roll
        self.roll_second = roll
        self.outcome = outcome
        self.casualty_first = casualty
        self.effect_first = effect
        self.casualty_second = None
        self.effect_second = None

    def step(self, action):

        if self.outcome == OutcomeType.KNOCKED_OUT:

            if action.action_type == ActionType.USE_APOTHECARY:

                # Player is moved to reserves
                self.game.pitch_to_reserves(self.player)
                self.game.report(Outcome(OutcomeType.APOTHECARY_USED_KO, player=self.player, team=self.player.team))

            else:

                # Player is KO
                self.game.pitch_to_kod(self.player)
                self.game.report(Outcome(OutcomeType.APOTHECARY_USED_KO, player=self.player, team=self.player.team))

            return True

        elif self.outcome == OutcomeType.CASUALTY:

            if action.action_type == ActionType.USE_APOTHECARY:

                self.roll_second = DiceRoll([D6(), D8()], roll_type=RollType.CASUALTY_ROLL)
                result = self.roll_second.get_sum()
                n = min(61, max(38, result))
                self.casualty_second = CasualtyType(n)
                self.effect_second = Rules.casualty_effect[self.casualty_second]
                self.player.team.state.apothecary_available = False
                self.game.report(Outcome(OutcomeType.CASUALTY_APOTHECARY, player=self.player, team=self.player.team,
                                         rolls=[self.roll_first, self.roll_second]))
                self.waiting_apothecary = True

                return False

            if action.action_type == ActionType.SELECT_ROLL:

                effect = self.effect_first if action.idx == 0 else self.effect_second
                casualty = self.casualty_first if action.idx == 0 else self.casualty_second
                roll = self.roll_first if action.idx == 0 else self.roll_second

                # Apply casualty
                self.game.pitch_to_casualties(self.player, casualty, effect, apothecary=True)
                if effect == CasualtyEffect.NONE:
                    self.game.report(Outcome(OutcomeType.BADLY_HURT, player=self.player, team=self.player.team, rolls=[roll]))
                elif effect in Casualty.miss_next_game:
                    self.game.report(Outcome(OutcomeType.MISS_NEXT_GAME, player=self.player, team=self.player.team,
                                             rolls=[roll]))
                elif effect == CasualtyEffect.DEAD:
                    self.game.report(Outcome(OutcomeType.DEAD, player=self.player, team=self.player.team, rolls=[roll]))

        return True

    def available_actions(self):
        if self.outcome == OutcomeType.KNOCKED_OUT or self.waiting_apothecary:
            return [ActionChoice(ActionType.USE_APOTHECARY, team=self.player.team),
                    ActionChoice(ActionType.DONT_USE_APOTHECARY, team=self.player.team)]
        else:
            return [ActionChoice(ActionType.SELECT_ROLL, team=self.player.team, indexes=[0, 1])]


class Armor(Procedure):

    def __init__(self, game, player, modifiers=0, inflictor=None, foul=False):
        super().__init__(game)
        self.player = player
        self.modifiers = modifiers
        self.inflictor = inflictor
        self.skip_armor = False
        self.armor_rolled = False
        self.foul = foul
        self.inflictor = inflictor

    def step(self, action):

        # Roll
        roll = DiceRoll([D6(), D6()], roll_type=RollType.ARMOR_ROLL)
        roll.modifiers = self.modifiers
        roll.target = self.player.get_av() + 1
        result = roll.get_sum() + self.modifiers
        self.armor_rolled = True

        armor_broken = False
        mighty_blow_used = False
        dirty_player_used = False

        if not self.foul:
            # Armor broken - Claws
            if roll.sum >= 8 and self.inflictor is not None and self.inflictor.has_skill(Skill.CLAWS):
                armor_broken = True

            # Armor broken
            if result >= roll.target:
                armor_broken = True

            # Armor broken - Might Blow
            if self.inflictor is not None and self.inflictor.has_skill(Skill.MIGHTY_BLOW) \
                    and result + 1 > self.player.get_av():
                roll.modifiers += 1
                armor_broken = True
                mighty_blow_used = True
        else:

            # Armor broken - Dirty player
            if self.inflictor is not None and self.inflictor.has_skill(Skill.DIRTY_PLAYER) \
                    and result + 1 > self.player.get_av():
                roll.modifiers += 1
                armor_broken = True
                dirty_player_used = True

            # Armor broken
            if result >= roll.target:
                armor_broken = True

        # EJECTION?
        ejected = False
        if self.foul:
            if roll.same():
                if not self.inflictor.has_skill(Skill.SNEAKY_GIT) or armor_broken:
                    self.game.report(Outcome(OutcomeType.PLAYER_EJECTED, player=self.inflictor))
                    Turnover(self.game)
                    Ejection(self.game, self.player)
                    ejected = True

        # Break armor - roll injury
        if armor_broken:
            Injury(self.game, self.player, self.inflictor, foul=self.foul,
                   mighty_blow_used=mighty_blow_used, dirty_player_used=dirty_player_used, ejected=ejected)
            self.game.report(Outcome(OutcomeType.ARMOR_BROKEN, player=self.player, opp_player=self.inflictor,
                                     rolls=[roll]))
        else:
            self.game.report(Outcome(OutcomeType.ARMOR_NOT_BROKEN, player=self.player, opp_player=self.inflictor,
                                     rolls=[roll]))

        return True

    def available_actions(self):
        return []


class Block(Procedure):

    @staticmethod
    def dice_and_favor(game, attacker, defender, blitz=False, dauntless_success=False):

        # Determine dice and favor
        st_from = attacker.get_st()
        st_to = defender.get_st()

        # Horns
        if blitz and attacker.has_skill(Skill.HORNS):
            st_from += 1

        # Dauntless
        if dauntless_success:
            st_from = st_to

        # Find assists
        assists_from = game.assists(attacker, defender)
        assists_to = game.assists(defender, attacker)
        st_from = st_from + len(assists_from)
        st_to = st_to + len(assists_to)

        # Determine dice and favor
        if st_from * 2 < st_to:
            return 3, defender.team
        elif st_from < st_to:
            return 2, defender.team
        elif st_from == st_to:
            return 1, attacker.team
        elif st_from > st_to * 2:
            return 3, attacker.team
        elif st_from > st_to:
            return 2, attacker.team

    def __init__(self, game, attacker, defender, blitz=False, frenzy=False, gfi=False):
        super().__init__(game)
        self.attacker = attacker
        self.defender = defender
        self.reroll_used = False
        self.roll = None
        self.blitz = blitz
        self.gfi = gfi
        self.frenzy = frenzy
        self.waiting_wrestle_attacker = False
        self.waiting_wrestle_defender = False
        self.selected_die = None
        self.wrestle = False
        self.favor = None
        self.dauntless_roll = None
        self.dauntless_success = False
        self.frenzy_check = False
        self.waiting_gfi = False

    def step(self, action):

        # GfI
        if self.gfi:
            self.gfi = False
            GFI(self.game, self.attacker, self.attacker.position)
            return False

        # Frenzy check
        if self.frenzy and not self.frenzy_check:
            # Check if player was not pushed out of bounds
            if self.defender.position is None:
                return True
            self.game.report(Outcome(OutcomeType.FRENZY_USED, player=self.attacker, opp_player=self.defender,
                                     team=self.attacker.team))
            self.frenzy_check = True

        # Roll
        if self.roll is None:

            # Assists
            if self.defender.get_st() > self.attacker.get_st() and self.attacker.has_skill(Skill.DAUNTLESS) \
                    and self.dauntless_roll is None:
                self.dauntless_roll = DiceRoll([D6()], roll_type=RollType.STRENGTH_ROLL)
                self.dauntless_success = self.dauntless_roll.get_sum() + self.attacker.get_st() > self.defender.get_st()
                self.game.report(Outcome(OutcomeType.DAUNTLESS_USED, team=self.attacker.team, player=self.attacker,
                                         rolls=[self.dauntless_roll], n=True))
                return False

            dice, self.favor = Block.dice_and_favor(self.game, self.attacker, self.defender,
                                                    blitz=self.blitz, dauntless_success=self.dauntless_success)

            # Roll
            self.roll = DiceRoll([], roll_type=RollType.BLOCK_ROLL)
            for i in range(dice):
                self.roll.dice.append(BBDie())

            self.game.report(Outcome(OutcomeType.BLOCK_ROLL, player=self.attacker, opp_player=self.defender,
                                     rolls=[self.roll]))

            return False

        elif self.waiting_wrestle_defender and action.team_id != self.defender.team.team_id:

            self.wrestle = action.action_type == ActionType.USE_WRESTLE
            self.waiting_wrestle_defender = False
            self.selected_die = BBDieResult.BOTH_DOWN

        elif action.action_type == ActionType.USE_REROLL:

            # Roll again
            self.reroll_used = True
            self.attacker.team.state.use_reroll()
            self.game.report(Outcome(OutcomeType.REROLL_USED, team=self.attacker.team))
            self.roll = None
            return self.step(None)

        elif action.action_type == ActionType.DONT_USE_REROLL:
            # Roll again
            self.reroll_used = True

        elif action.action_type == ActionType.USE_JUGGERNAUT:
            self.selected_die = BBDieResult.PUSH

        elif action.action_type == ActionType.SELECT_DIE:
            die = self.roll.dice[action.idx]
            self.selected_die = die.get_value()

        # Dice result
        if self.selected_die == BBDieResult.ATTACKER_DOWN:
            Turnover(self.game)
            KnockDown(self.game, self.attacker, inflictor=self.defender)
            return True

        if self.selected_die == BBDieResult.BOTH_DOWN:
            if not self.attacker.has_skill(Skill.BLOCK):
                Turnover(self.game)
                KnockDown(self.game, self.attacker, inflictor=self.defender)
            else:
                self.game.report(Outcome(OutcomeType.SKILL_USED, player=self.attacker, skill=Skill.BLOCK))
            if not self.defender.has_skill(Skill.BLOCK):
                KnockDown(self.game, self.defender, inflictor=self.attacker)
            else:
                self.game.report(Outcome(OutcomeType.SKILL_USED, player=self.defender, skill=Skill.BLOCK))
            return True

        if self.selected_die == BBDieResult.DEFENDER_DOWN:
            Push(self.game, self.attacker, self.defender, knock_down=True, blitz=self.blitz)
            return True

        if self.selected_die == BBDieResult.DEFENDER_STUMBLES:
            Push(self.game, self.attacker, self.defender, knock_down=not self.defender.has_skill(Skill.DODGE),
                 blitz=self.blitz)
            return True

        if self.selected_die == BBDieResult.PUSH:
            Push(self.game, self.attacker, self.defender, knock_down=False, blitz=self.blitz)
            return True

        return False

    def available_actions(self):

        actions = []

        if self.roll is not None and self.selected_die is None:
            disable_dice_pick = False
            if self.game.can_use_reroll(self.attacker.team) and not self.reroll_used:
                actions.append(ActionChoice(ActionType.USE_REROLL, self.attacker.team))
                if self.favor != self.attacker.team:
                    actions.append(ActionChoice(ActionType.DONT_USE_REROLL, self.defender.team))
                    disable_dice_pick = True

            indexes = [i for i in range(len(self.roll.dice))]
            dice = [die for die in self.roll.dice]
            actions.append(ActionChoice(ActionType.SELECT_DIE, self.favor, indexes=indexes, dice=dice,
                                        disabled=disable_dice_pick))

        return actions


class Bounce(Procedure):

    def __init__(self, game, ball, kick=False):
        super().__init__(game)
        self.ball = ball
        self.kick = kick

    def step(self, action):

        # Loose control
        self.ball.carried = False

        # Roll
        roll_scatter = DiceRoll([D8()], roll_type=RollType.BOUNCE_ROLL)
        result = roll_scatter.get_sum()

        # Bounce
        x = 0
        y = 0
        if result in [1, 4, 6]:
            x = -1
        if result in [3, 5, 9]:
            x = 1
        if result in [1, 2, 3]:
            y = -1
        if result in [6, 7, 8]:
            y = 1

        self.ball.move(x, y)
        self.game.report(Outcome(OutcomeType.BALL_BOUNCED, pos=self.ball.position, rolls=[roll_scatter]))

        if self.kick:
            # Touchback
            if not self.game.is_team_side(self.ball.position, self.game.get_receiving_team()):
                Touchback(self.game, self.ball)
                self.game.report(Outcome(OutcomeType.TOUCHBACK, team=self.game.get_receiving_team(),
                                         rolls=[roll_scatter]))
                return True
        else:
            # Out of bounds
            if self.game.is_out_of_bounds(self.ball.position):
                # Move ball back
                self.ball.move(-x, -y)
                ThrowIn(self.game, self.ball)
                self.game.report(Outcome(OutcomeType.BALL_OUT_OF_BOUNDS, rolls=[roll_scatter]))
                return True

        # On player -> Catch
        player_at = self.game.get_player_at(self.ball.position)
        if player_at is not None:
            Catch(self.game, player_at, self.ball)
            self.game.report(Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.ball.position,
                                     player=player_at, rolls=[roll_scatter]))
            return True

        self.game.report(Outcome(OutcomeType.BALL_ON_GROUND, pos=self.ball.position))
        return True

    def available_actions(self):
        return []


class Casualty(Procedure):

    miss_next_game = [CasualtyEffect.MNG, CasualtyEffect.AG, CasualtyEffect.AV, CasualtyEffect.MA, CasualtyEffect.ST,
                      CasualtyEffect.NI]

    def __init__(self, game, player, roll, inflictor=None):
        super().__init__(game)
        self.game = game
        self.player = player
        self.inflictor = inflictor
        self.waiting_apothecary = False
        self.roll = roll
        self.casualty = None
        self.effect = None

    def step(self, action):

        self.roll = DiceRoll([D6(), D8()], d68=True, roll_type=RollType.CASUALTY_ROLL)
        result = self.roll.get_sum()
        n = min(61, max(38, result))
        self.casualty = CasualtyType(n)
        self.effect = Rules.casualty_effect[self.casualty]

        if self.game.has_apothecary_available(self.player.team):
            self.game.report(
                Outcome(OutcomeType.CASUALTY, player=self.player, team=self.player.team, n=self.effect.name,
                        rolls=[self.roll]))
            Apothecary(self.game, self.player, roll=self.roll, outcome=OutcomeType.CASUALTY,
                       casualty=self.casualty, effect=self.effect, inflictor=self.inflictor)
        else:
            # Apply casualty
            self.game.pitch_to_casualties(self.player, self.casualty, self.effect)
            if self.effect == CasualtyEffect.NONE:
                self.game.report(Outcome(OutcomeType.BADLY_HURT, player=self.player, team=self.player.team,
                                         rolls=[self.roll]))
            elif self.effect in Casualty.miss_next_game:
                self.game.report(Outcome(OutcomeType.MISS_NEXT_GAME, player=self.player, team=self.player.team,
                                         rolls=[self.roll], n=self.effect.name))
            elif self.effect == CasualtyEffect.DEAD:
                self.game.report(Outcome(OutcomeType.DEAD, player=self.player, team=self.player.team,
                                         rolls=[self.roll]))

        return True

    def available_actions(self):
        return []


class Catch(Procedure):

    #          0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    success = [6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1]

    @staticmethod
    def catch_modifiers(game, player, accurate=False, interception=False, handoff=False):
        modifiers = 1 if accurate or handoff else 0
        modifiers = -2 if interception else modifiers
        if interception and player.has_skill(Skill.LONG_LEGS):
            modifiers += 1
        tackle_zones = game.tackle_zones_in(player.position)
        modifiers -= tackle_zones
        if game.state.weather == WeatherType.POURING_RAIN:
            modifiers -= 1
        if player.has_skill(Skill.EXTRA_ARMS):
            modifiers += 1
        return modifiers

    def __init__(self, game, player, ball, accurate=False, interception=False, handoff=True):
        super().__init__(game)
        self.player = player
        self.ball = ball
        self.accurate = accurate
        self.handoff = handoff
        self.rolled = False
        self.reroll_used = False
        self.catch_used = False
        self.waiting_for_reroll = False
        self.waiting_for_catch = False
        self.interception = interception

    def step(self, action):

        # Otherwise roll if player hasn't rolled
        if not self.rolled:

            # Can player even catch ball?
            if self.player.has_skill(Skill.NO_HANDS) or self.player.state.ready not in Rules.catchable:
                Bounce(self.game, self.ball)
                self.game.report(Outcome(OutcomeType.BALL_DROPPED, player=self.player))
                return True

            # Set modifiers
            modifiers = Catch.catch_modifiers(self.game, self.player, accurate=self.accurate,
                                              interception=self.interception, handoff=self.handoff)

            # Roll
            roll = DiceRoll([D6()], roll_type=RollType.AGILITY_ROLL)
            roll.modifiers = modifiers
            roll.target = Catch.success[self.player.get_ag()]
            self.rolled = True
            if roll.is_d6_success():
                if self.interception:
                    self.game.report(Outcome(OutcomeType.INTERCEPTION, player=self.player, rolls=[roll]))
                    self.ball.move_to(self.player.position)
                    self.ball.carried = True
                    if self.game.is_touchdown(self.player):
                        Touchdown(self.game, self.player)
                    else:
                        Turnover(self.game)
                else:
                    self.game.report(Outcome(OutcomeType.CATCH, player=self.player, rolls=[roll]))
                    self.ball.carried = True
                    if self.game.is_touchdown(self.player):
                        Touchdown(self.game, self.player)
                return True
            else:

                if self.interception:
                    self.game.report(Outcome(OutcomeType.INTERCEPTION_FAILED, player=self.player, rolls=[roll]))
                    return True

                self.game.report(Outcome(OutcomeType.CATCH_FAILED, player=self.player, rolls=[roll]))

                # Check if catch
                if self.player.has_skill(Skill.CATCH) and not self.catch_used:
                    self.catch_used = True
                    self.waiting_for_catch = True
                    self.game.report(Outcome(OutcomeType.SKILL_USED, player=self.player, skill=Skill.CATCH))
                    return False

                # Check if reroll available
                if self.game.can_use_reroll(self.player.team) and not self.catch_used:
                    self.waiting_for_reroll = True
                    return False

                Bounce(self.game, self.ball)
                return True

        # If catch used
        if self.waiting_for_catch:
            self.catch_used = True
            self.rolled = False
            return self.step(None)

        # If re-roll used
        if self.waiting_for_reroll:
            if action.action_type == ActionType.USE_REROLL:
                self.reroll_used = True
                self.player.team.state.use_reroll()
                self.game.report(Outcome(OutcomeType.REROLL_USED, team=self.player.team))
                self.rolled = False
                return self.step(None)
            else:
                Bounce(self.game, self.ball)

        return True

    def available_actions(self):
        if self.waiting_for_reroll:
            return [ActionChoice(ActionType.USE_REROLL, team=self.player.team),
                    ActionChoice(ActionType.DONT_USE_REROLL, team=self.player.team)]
        return []


class CoinToss(Procedure):

    def __init__(self, game):
        super().__init__(game)
        self.away_won_toss = None
        self.aa = [ActionChoice(ActionType.HEADS, team=False),
                   ActionChoice(ActionType.TAILS, team=False)]

    def step(self, action):
        if self.away_won_toss is None:
            self._flip_coin(action)
            return False
        elif self.away_won_toss is not None:
            self._pick(action)
            return True

    def _flip_coin(self, action):
        if action.action_type == ActionType.HEADS:
            if random.random() >= 0.5:
                self.away_won_toss = True
                self.game.report(Outcome(OutcomeType.HEADS_WON))
            else:
                self.away_won_toss = False
                self.game.report(Outcome(OutcomeType.HEADS_LOSS))
        elif action.action_type == ActionType.TAILS:
            if random.random() >= 0.5:
                self.away_won_toss = True
                self.game.report(Outcome(OutcomeType.TAILS_WON))
            else:
                self.away_won_toss = False
                self.game.report(Outcome(OutcomeType.TAILS_LOSS))

        self.aa = [ActionChoice(ActionType.KICK, team=not self.away_won_toss),
                   ActionChoice(ActionType.RECEIVE, team=not self.away_won_toss)]

    def _pick(self, action):
        kicking = None
        receiving = None
        if action.action_type == ActionType.KICK:
            kicking = self.game.get_opp_team(self.game.home_team) if self.away_won_toss else self.game.home_team
            receiving = self.game.get_opp_team(self.game.home_team) if not self.away_won_toss else self.game.home_team
        elif action.action_type == ActionType.RECEIVE:
            kicking = self.game.get_opp_team(self.game.home_team) if not self.away_won_toss else self.game.home_team
            receiving = self.game.get_opp_team(self.game.home_team) if self.away_won_toss else self.game.home_team
        self.game.state.kicking_first_half = kicking
        self.game.state.kicking_this_drive = kicking
        self.game.state.receiving_first_half = receiving
        self.game.state.receiving_this_drive = receiving
        if receiving == self.game.state.home_team:
            self.game.report(Outcome(OutcomeType.HOME_RECEIVE, team=receiving))
        else:
            self.game.report(Outcome(OutcomeType.AWAY_RECEIVE, team=receiving))

    def available_actions(self):
        return self.aa


class Ejection(Procedure):

    def __init__(self, game, player):
        super().__init__(game)
        self.player = player

    def step(self, action):

        self.game.pitch_to_dungeon(self.player)
        return True

    def available_actions(self):
        return []


class Foul(Procedure):

    def __init__(self, game, fouler, defender):
        super().__init__(game)
        self.fouler = fouler
        self.defender = defender

    def step(self, action):

        # Assists
        assists_from = self.game.assists(self.fouler, self.defender, ignore_guard=True)
        assists_to = self.game.assists(self.defender, self.fouler, ignore_guard=True)
        modifier = len(assists_from) - len(assists_to)

        self.game.report(Outcome(OutcomeType.FOUL, player=self.fouler, opp_player=self.defender))

        # Armor roll
        Armor(self.game, self.defender, modifiers=modifier, inflictor=self.fouler, foul=True)

        return True

    def available_actions(self):
        return []


class ResetHalf(Procedure):

    def __init__(self, game):
        super().__init__(game)

    def step(self, action):
        for team in self.game.teams:
            team.state.rerolls = team.rerolls
            team.state.turn = 0
        return True

    def available_actions(self):
        return []


class Half(Procedure):

    def __init__(self, game, half):
        super().__init__(game)
        self.half = half
        self.kicked_off = False

        # If second half
        if self.half > 1:
            PreHalf(self.game, False)
            PreHalf(self.game, True)

    def step(self, action):

        self.game.state.half = self.half
        self.game.state.kicking_team_this_drive = self.game.get_kicking_team(self.half)
        self.game.state.receiving_team_this_drive = self.game.get_receiving_team(self.half)

        # Kickoff
        if not self.kicked_off:
            self.kicked_off = True
            self.game.set_turn_order(self.game.get_kicking_team(self.half))
            KickOff(self.game)
            Setup(self.game, team=self.game.get_receiving_team(self.half))
            Setup(self.game, team=self.game.get_kicking_team(self.half))
            ResetHalf(self.game)
            ClearBoard(self.game)
            return False

        # Add turn in round
        if self.game.state.round < self.game.config.rounds:
            self.game.state.round += 1
            for team in self.game.state.turn_order:
                Turn(self.game, team, self.half, self.game.state.round)
            return False

        if self.half == 1:
            self.game.report(Outcome(OutcomeType.END_OF_FIRST_HALF))
        elif self.half == 2:
            self.game.report(Outcome(OutcomeType.END_OF_SECOND_HALF))

        return True

    def available_actions(self):
        return []


class Injury(Procedure):

    def __init__(self, game, player, inflictor=None, foul=False, mighty_blow_used=False, dirty_player_used=False,
                 ejected=False, in_crowd=False):
        super().__init__(game)
        self.game = game
        self.player = player
        self.inflictor = inflictor
        self.injury_rolled = False
        self.foul = foul
        self.mighty_blow_used = mighty_blow_used
        self.dirty_player_used = dirty_player_used
        self.ejected = ejected
        self.apothecary_used = False
        self.in_crowd = in_crowd

    def step(self, action):

        # TODO: Necromancer

        # Roll
        roll = DiceRoll([D6(), D6()], roll_type=RollType.INJURY_ROLL)
        result = roll.get_sum()
        self.injury_rolled = True

        # Skill modifiers
        thick_skull = -1 if self.player.has_skill(Skill.THICK_SKULL) else 0
        stunty = 1 if self.player.has_skill(Skill.STUNTY) else 0
        mighty_blow = 0
        dirty_player = 0
        if self.inflictor is not None:
            dirty_player = 1 if self.inflictor.has_skill(Skill.DIRTY_PLAYER) and not self.dirty_player_used and \
                                self.foul else 0
            mighty_blow = 1 if self.inflictor.has_skill(Skill.MIGHTY_BLOW) and not self.mighty_blow_used and not \
                self.foul else 0

        # EJECTION
        if self.foul and not self.ejected:
            if roll.same():
                if not self.inflictor.has_skill(Skill.SNEAKY_GIT):
                    self.game.report(Outcome(OutcomeType.PLAYER_EJECTED, player=self.inflictor))
                    Turnover(self.game)
                    Ejection(self.game, self.inflictor)

        # STUNNED
        if result + thick_skull + stunty + mighty_blow + dirty_player <= 7:
            roll.modifiers = thick_skull + stunty + mighty_blow + dirty_player
            if self.player.has_skill(Skill.BALL_AND_CHAIN):
                KnockOut(self.game, self.player, roll=roll, inflictor=self.inflictor)
            else:
                self.game.report(Outcome(OutcomeType.STUNNED, player=self.player, opp_player=self.inflictor,
                                         rolls=[roll]))
                if self.in_crowd:
                    self.game.pitch_to_reserves(self.player)
                else:
                    self.player.state.ready = PlayerReadyState.STUNNED

        # CASUALTY
        elif result + stunty + mighty_blow + dirty_player >= 10:
            roll.modifiers = stunty + mighty_blow + dirty_player
            self.game.report(Outcome(OutcomeType.CASUALTY, player=self.player, opp_player=self.inflictor, rolls=[roll]))
            Casualty(self.game, self.player, roll, inflictor=self.inflictor)

        # KOD
        else:
            roll.modifiers = thick_skull + stunty + mighty_blow + dirty_player
            KnockOut(self.game, self.player, roll=roll, inflictor=self.inflictor)

        return True

    def available_actions(self):
        return []


class Interception(Procedure):

    def __init__(self, game, team, ball, interceptors):
        super().__init__(game)
        self.team = team
        self.ball = ball
        self.interceptors = interceptors

    def step(self, action):

        if action.action_type == ActionType.INTERCEPTION:
            interceptor = self.game.get_player(action.player_from_id)
            self.ball.move_to(interceptor.position)
            Catch(self.game, interceptor, self.ball, interception=True)

        return True

    def available_actions(self):
        return [ActionChoice(ActionType.INTERCEPTION, team=self.team, players=self.interceptors,
                             agi_rolls=[[Catch.catch_modifiers(self.game, interceptor, interception=True)]
                                        for interceptor in self.interceptors]),
                ActionChoice(ActionType.SELECT_NONE, team=self.team)]


class Touchback(Procedure):

    def __init__(self, game, ball):
        super().__init__(game)
        self.reciving_team = self.game.get_reciving_team()  # Player who can place the ball
        self.ball = ball

    def step(self, action):
        player = self.game.get_player(action.player_from_id)
        pos = self.game.get_player_position(player)
        self.ball.move_to(pos)
        self.ball.carried = True
        self.game.report(Outcome(OutcomeType.TOUCHBACK_BALL_PLACED, player=player, pos=pos))
        return True

    def available_actions(self):
        return [ActionChoice(ActionType.SELECT_PLAYER, team=self.reciving_team,
                             players=self.game.get_players_on_pitch(self.reciving_team, ready=PlayerReadyState.READY))]


class LandKick(Procedure):

    def __init__(self, game, ball):
        super().__init__(game)
        self.ball = ball
        self.landed = False

    def step(self, action):

        if not self.game.arena.is_team_side(self.ball.position, self.game.get_receiving_team()):
            Touchback(self.game, self.ball)
            self.game.report(Outcome(OutcomeType.TOUCHBACK, team=self.game.get_receiving_team()))
            return True

        # Gentle gust
        if self.game.state.gentle_gust:
            Scatter(self.game, self.ball, kick=True, gentle_gust=True)
            self.game.state.gentle_gust = False
            return False

        self.ball.in_air = False
        player_at = self.game.get_player_at(self.ball.position)
        if player_at is None:
            Bounce(self.game, self.ball, kick=True)
            self.game.report(Outcome(OutcomeType.BALL_HIT_GROUND, pos=self.ball.position))
            return True

        Catch(self.game, player_at, self.ball)
        self.game.report(Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.ball.position, player=player_at))

        return True

    def available_actions(self):
        return []


class Fans(Procedure):

    def __init__(self, game):
        super().__init__(game)

    def step(self, action):

        # Fans
        rolls = []
        spectators = []
        for team_id, team in self.game.teams.items():
            roll = DiceRoll([D6(), D6()], roll_type=RollType.FANS_ROLL)
            rolls.append(roll)
            fans = (roll.get_sum() + team.fan_factor) * 1000
            spectators.append(fans)
            self.game.report(Outcome(OutcomeType.TEAM_SPECTATORS, n=fans, team=team, rolls=[roll]))
        self.game.set_spectators(np.sum(spectators))
        self.game.report(Outcome(OutcomeType.SPECTATORS, n=self.game.get_spectators()))

        # FAME
        fame = []
        max_fans = np.max(spectators)
        min_fans = np.min(spectators)
        for i in range(len(self.game.teams.keys())):
            team = self.game.teams[self.game.teams.keys()[i]]
            fans = spectators[i]
            if fans == max_fans:
                if fans >= min_fans * 2:
                    fame.append(2)
                    self.game.report(Outcome(OutcomeType.FAME, n=fame, team=team))
                elif fans > fans:
                    fame.append(1)
                    self.game.report(Outcome(OutcomeType.FAME, n=fame, team=team))
                else:
                    fame.append(0)
                    self.game.report(Outcome(OutcomeType.NO_FAME, n=fame, team=team))
            self.game.set_fame(team, fame[i])

        return True

    def available_actions(self):
        return []


class KickOff(Procedure):

    def __init__(self, game):
        super().__init__(game)
        self.game.state.gentle_gust = False
        self.game.state.reset_kickoff()
        ball = Ball(None, on_ground=False)
        LandKick(game, ball)
        KickoffTable(game, ball)
        Scatter(game, ball, kick=True)
        PlaceBall(game, ball)

    def step(self, action):
        return True

    def available_actions(self):
        return []


class GetTheRef(Procedure):
    """
    Each team receives 1 additional Bribe to use during this game.
    """
    def __init__(self, game):
        super().__init__(game)

    def step(self, action):
        for team in self.game.teams:
            team.state.bribes += 1
            self.game.report(Outcome(OutcomeType.EXTRA_BRIBE, team=team))
        return True

    def available_actions(self):
        return []


class Riot(Procedure):
    """
    The trash talk between two opposing players explodes and rapidly degenerates, involving the rest of the players.
    If the receiving team's turn marker is on turn 7 for the half, both teams move their turn marker back one space as
    the referee resets the clock back to before the fight started. If the receiving team has not yet taken a turn this
    half the referee lets the clock run on during the fight and both teams' turn markers are moved forward one space.
    Otherwise roll a D6. On a 1-3, both teams' turn markers are moved forward one space. On a 4-6, both team's turn
    markers are moved back one space.
    """
    def __init__(self, game):
        super().__init__(game)
        self.effect = 0

    def step(self, action):
        roll = None
        receiving_turn = self.game.get_team_turn(self.game.get_receiving_team())
        if receiving_turn == 7:
            self.effect = -1
        elif receiving_turn == 0:
            self.effect = 1
        else:
            roll = DiceRoll([D6()], roll_type=RollType.RIOT_ROLL)
            if roll.get_sum() <= 3:
                self.effect = 1
            else:
                self.effect = -1

        self.game.add_or_skip_turn(self.effect)
        if self.effect == -1:
            self.game.report(Outcome(OutcomeType.TURN_ADDED, rolls=[] if roll is None else [roll]))
        if self.effect == 1:
            self.game.report(Outcome(OutcomeType.TURN_SKIPPED, rolls=[] if roll is None else [roll]))

        return True

    def available_actions(self):
        return []


class HighKick(Procedure):
    """
    High Kick: The ball is kicked very high, allowing a player on the receiving team time to move into the
    perfect position to catch it. Any one player on the receiving team who is not in an opposing player's
    tackle zone may be moved into the square where the ball will land no matter what their MA may be, as long
    as the square is unoccupied.
    """
    def __init__(self, game, ball):
        super().__init__(game)
        self.ball = ball
        self.receiving_team = self.game.get_receiving_team()

    def step(self, action):
        if action.action_type == ActionType.PLACE_PLAYER:
            self.game.move(self.game.get_player(action.player_from_id), action.pos_to)
            self.game.report(Outcome(OutcomeType.PLAYER_PLACED_HIGH_KICK, pos=action.pos_to, team=self.receiving_team))
        elif action.action_type == ActionType.END_SETUP:
            self.game.report(Outcome(OutcomeType.SETUP_DONE, team=self.receiving_team))
        return True

    def available_actions(self):
        if self.game.arena.is_team_side(self.ball.position, self.receiving_team) and \
                self.game.get_player_at(self.ball.position) is None:
            return [ActionChoice(ActionType.PLACE_PLAYER, team=self.receiving_team,
                                 players=self.game.get_players_on_pitch(self.receiving_team),
                                 positions=[self.ball.position]),
                    ActionChoice(ActionType.SELECT_NONE, team=self.receiving_team)]
        else:
            return [ActionChoice(ActionType.SELECT_NONE, team=self.receiving_team)]


class CheeringFans(Procedure):
    """
    Each coach rolls a D3 and adds their team's FAME (see page 18) and the number of cheerleaders on their team to the
    score. The team with the highest score is inspired by their fans' cheering and gets an extra re-roll this half.
    If both teams have the same score, then both teams get a re-roll.
    """
    def __init__(self, game):
        super().__init__(game)

    def step(self, action):
        rolls = []
        cheers = []
        for team_id, team in self.game.teams.items():
            roll = DiceRoll([D3()], roll_type=RollType.CHEERING_FANS_ROLL)
            rolls.append(roll)
            roll.modifiers = team.state.fame + team.cheerleaders
            cheers.append(roll.get_result())
            self.game.report(Outcome(OutcomeType.CHEERING_FANS_ROLL, team=team, rolls=[roll]))

        max_cheers = np.max(cheers)
        for i in range(len(self.game.teams.keys())):
            team = self.game.teams[self.game.teams.keys()[i]]
            if max_cheers == cheers[i]:
                team.state.rerolls += 1
                self.game.report(Outcome(OutcomeType.EXTRA_REROLL, team=team))

        return True

    def available_actions(self):
        return []


class BrilliantCoaching(Procedure):
    """
    Each coach rolls a D3 and adds their FAME (see page 18) and the number of assistant coaches on their team to the
    score. The team with the highest total gets an extra team re-roll this half thanks to the brilliant instruction
    provided by the coaching staff. In case of a tie both teams get an extra team re-roll.
    """
    def __init__(self, game):
        super().__init__(game)

    def step(self, action):

        rolls = []
        brilliant_coaches = []
        for team_id, team in self.game.teams.items():
            roll = DiceRoll([D3()], roll_type=RollType.BRILLIANT_COACHING_ROLL)
            rolls.append(roll)
            roll.modifiers = self.game.get_fame(team) + self.game.get_ass_coaches(team)
            brilliant_coaches.append(roll.get_result())
            self.game.report(Outcome(OutcomeType.BRILLIANT_COACHING_ROLL, team=team, rolls=[roll]))

        max_cheers = np.max(brilliant_coaches)
        for i in range(len(self.game.teams.keys())):
            team = self.game.teams[self.game.teams.keys()[i]]
            if max_cheers == brilliant_coaches[i]:
                team.state.rerolls += 1
                self.game.report(Outcome(OutcomeType.EXTRA_REROLL, team=team))

        return True

    def available_actions(self):
        return []


class ThrowARock(Procedure):
    """
    An enraged fan hurls a large rock at one of the players on the opposing team. Each coach rolls a D6 and adds their
    FAME (see page 18) to the roll. The fans of the team that rolls higher are the ones that threw the rock. In the
    case of a tie a rock is thrown at each team! Decide randomly which player in the other team was hit (only players
    on the pitch are eligible) and roll for the effects of the injury straight away. No Armour roll is required.
    """
    def __init__(self, game):
        super().__init__(game)
        self.rolled = False

    def step(self, action):

        rolls = []
        rocks = []
        for team_id, team in self.game.teams.items():
            roll = DiceRoll([D3()], roll_type=RollType.THROW_A_ROCK_ROLL)
            rolls.append(roll)
            roll.modifiers = self.game.get_fame(team)
            rocks.append(roll.get_result())
            self.game.report(Outcome(OutcomeType.THROW_A_ROCK_ROLL, team=team, rolls=[roll]))

        max_cheers = np.max(rocks)
        for i in range(len(self.game.teams.keys())):
            team = self.game.teams[self.game.teams.keys()[i]]
            if max_cheers >= rocks[i]:
                player = np.random.sample(self.game.get_players_on_pitch(team))
                KnockDown(self.game, player, armor_roll=False)
                self.game.report(Outcome(OutcomeType.HIT_BY_ROCK, player=player))

        return True

    def available_actions(self):
        return []


class PitchInvasionRoll(Procedure):
    """
    ... If a roll is 6 or more after modification then the player is Stunned (players with the Ball & Chain skill are
    KO'd). A roll of 1 before adding FAME will always have no effect.
    """
    def __init__(self, game, team, player):
        super().__init__(game)
        self.team = team
        self.player = player

    def step(self, action):
        roll = DiceRoll([D6()], roll_type=RollType.PITCH_INVASION_ROLL)

        roll.modifiers = self.game.get_fame(self.team)
        result = roll.get_sum() + roll.modifiers

        if result >= 6:
            if self.player.has_skill(Skill.BALL_AND_CHAIN):
                self.game.report(Outcome(OutcomeType.KNOCKED_OUT, rolls=[roll], player=self.player, team=self.team))
                KnockOut(self.game, self.player, roll=roll)
            else:
                self.player.state.ready = PlayerReadyState.STUNNED
                self.game.report(Outcome(OutcomeType.STUNNED, rolls=[roll], player=self.player, team=self.team))
        else:
            self.game.report(Outcome(OutcomeType.PLAYER_READY, rolls=[roll], player=self.player, team=self.team))

        return True

    def available_actions(self):
        return []


class KickoffTable(Procedure):

    def __init__(self, game, ball):
        super().__init__(game)
        self.ball = ball
        self.rolled = False

    def step(self, action):

        roll = DiceRoll([D6(), D6()], roll_type=RollType.KICKOFF_ROLL)
        roll.result = roll.get_sum()

        self.rolled = True

        if roll.result == 2:  # Get the ref!
            GetTheRef(self.game)
            self.game.report(Outcome(OutcomeType.KICKOFF_GET_THE_REF, rolls=[roll]))
        elif roll.result == 3:  # Riot!
            Riot(self.game)
            self.game.report(Outcome(OutcomeType.KICKOFF_RIOT, rolls=[roll]))
        elif roll.result == 4:  # Perfect defense
            Setup(self.game, team=self.game.get_kicking_team(), reorganize=True)
            self.game.report(Outcome(OutcomeType.KICKOFF_PERFECT_DEFENSE, team=self.game.get_kicking_team(),
                                     rolls=[roll]))
        elif roll.result == 5:  # High Kick
            HighKick(self.game, self.ball)
            self.game.report(Outcome(OutcomeType.KICKOFF_HIGH_KICK, rolls=[roll]))
        elif roll.result == 6:  # Cheering fans
            CheeringFans(self.game)
            self.game.report(Outcome(OutcomeType.KICKOFF_CHEERING_FANS, rolls=[roll]))
        elif roll.result == 7:  # Changing Weather
            WeatherTable(self.game, kickoff=True)
            self.game.report(Outcome(OutcomeType.KICKOFF_CHANGING_WHEATHER, rolls=[roll]))
        elif roll.result == 8:  # Brilliant Coaching
            BrilliantCoaching(self.game)
            self.game.report(Outcome(OutcomeType.KICKOFF_BRILLIANT_COACHING, rolls=[roll]))
        elif roll.result == 9:  # Quick Snap
            Turn(self.game, self.game.get_receiving_team(), None, None, quick_snap=True)
            self.game.report(Outcome(OutcomeType.KICKOFF_QUICK_SNAP, rolls=[roll]))
        elif roll.result == 10:  # Blitz
            Turn(self.game, self.game.get_kicking_team(), None, None, blitz=True)
            self.game.report(Outcome(OutcomeType.KICKOFF_BLITZ, rolls=[roll]))
        elif roll.result == 11:  # Throw a Rock
            ThrowARock(self.game)
            self.game.report(Outcome(OutcomeType.KICKOFF_THROW_A_ROCK, rolls=[roll]))
        elif roll.result == 12:  # Pitch Invasion
            for team in self.game.teams:
                for player in self.game.get_players_on_pitch(team):
                    PitchInvasionRoll(self.game, team, player)
            self.game.report(Outcome(OutcomeType.KICKOFF_PITCH_INVASION, rolls=[roll]))

        return True

    def available_actions(self):
        return []


class KnockDown(Procedure):

    def __init__(self, game, player, armor_roll=True, injury_roll=True, modifiers=0, inflictor=None,
                 in_crowd=False, modifiers_opp=0, turnover=False):
        super().__init__(game)
        self.player = player
        self.armor_roll = armor_roll
        self.injury_roll = injury_roll
        self.modifiers = modifiers
        self.modifiers_opp = modifiers_opp
        self.inflictor = inflictor
        self.in_crowd = in_crowd
        self.turnover = turnover

    def step(self, action):

        # Knock down player
        self.player.state.ready = PlayerReadyState.DOWN_USED
        self.game.report(Outcome(OutcomeType.KNOCKED_DOWN, player=self.player, opp_player=self.inflictor))

        # Turnover
        if self.turnover:
            Turnover(self.game)

        # Check fumble
        ball = self.game.get_ball_at(self.player.position)
        if ball is not None:
            Bounce(self.game, ball)
            self.game.report(Outcome(OutcomeType.FUMBLE, player=self.player, opp_player=self.inflictor))

        # If armor roll should be made. Injury is also nested in armor.
        if self.injury_roll and not self.armor_roll:
            Injury(self.game, self.player, inflictor=self.inflictor if not self.in_crowd else None,
                   in_crowd=self.in_crowd)
        elif self.armor_roll:
            Armor(self.game, self.player, modifiers=self.modifiers, inflictor=self.inflictor)

        return True

    def available_actions(self):
        return []


class KnockOut(Procedure):

    def __init__(self, game, player, roll, inflictor=None):
        super().__init__(game)
        self.game = game
        self.player = player
        self.inflictor = inflictor
        self.inflictor_id = inflictor.player_id if inflictor is not None else None
        self.roll = roll

    def step(self, action):
        if self.game.has_apothecary_available(self.player.team):
            Apothecary(self.game, self.player, roll=self.roll, outcome=OutcomeType.KNOCKED_OUT,
                       inflictor=self.inflictor)
            return True
        else:
            # Knock out player
            self.game.pitch_to_kod(self.player)
            self.game.report(Outcome(OutcomeType.KNOCKED_OUT, rolls=[self.roll], player=self.player,
                                     opp_player=self.inflictor))

        return True

    def available_actions(self):
        return []


class Move(Procedure):

    def __init__(self, game, player, pos, gfi, dodge):
        super().__init__(game)
        self.player = player
        self.pos = pos
        if dodge:
            Dodge(game, player, pos)
        if gfi:
            GFI(game, player, pos)

    def step(self, action):

        self.game.move_player(self.player, self.pos)

        # Check if player moved onto the ball
        ball = self.game.get_ball_at(self.player)
        if ball is not None:

            # Attempt to pick up the ball - unless no hands
            if self.player.has_skill(Skill.NO_HANDS):
                Bounce(self.game, ball)
                return True
            else:
                Pickup(self.game, ball, self.player, cause_turnover=True)
                return True

        elif self.game.has_ball(self.player) and self.game.arena.is_touchdown(self.player):

            # Touchdown if player had the ball with him/her
            Touchdown(self.game, self.player)

        return True

    def available_actions(self):
        return []


class GFI(Procedure):

    def __init__(self, game, player, pos):
        super().__init__(game)
        self.player = player
        self.pos = pos
        self.awaiting_reroll = False
        self.awaiting_sure_feet = False
        self.sure_feet_used = False
        self.reroll_used = False
        self.rolled = False

    def step(self, action):

        # If player hasn't rolled
        if not self.rolled:

            # Roll
            roll = DiceRoll([D6()], roll_type=RollType.GFI_ROLL)
            self.rolled = True
            roll.target = 2
            roll.modifiers = 1 if self.game.state.weather == WeatherType.BLIZZARD else 0

            if roll.is_d6_success():

                # Success
                self.game.report(Outcome(OutcomeType.SUCCESSFUL_GFI, player=self.player, pos=self.pos, rolls=[roll]))
                return True

            else:

                # Fail
                self.game.report(Outcome(OutcomeType.FAILED_GFI, player=self.player, pos=self.pos, rolls=[roll]))

                # Check if sure feet
                if self.player.has_skill(Skill.SURE_FEET) and not self.sure_feet_used:
                    self.sure_feet_used = True
                    self.awaiting_sure_feet = True
                    self.game.report(Outcome(OutcomeType.SKILL_USED, player=self.player, skill=Skill.SURE_FEET))
                    return False

                # Check if reroll available
                if self.game.can_use_reroll(self.player.team) and not self.sure_feet_used:
                    self.awaiting_reroll = True
                    return False

                # Player trips
                if not self.player.position == self.pos:
                    self.game.move_player(self.player, self.pos)
                KnockDown(self.game, self.player, self.pos, turnover=True)
                return True

        # If sure feet used
        if self.awaiting_sure_feet:
            if action.action_type == ActionType.USE_SKILL:
                self.sure_feet_used = True
                self.rolled = False
                self.step(None)
            else:
                # Player trips
                self.game.move_player(self.player, self.pos)
                KnockDown(self.game, self.player, turnover=True)
                return True

        # If reroll used
        if self.awaiting_reroll:
            if action.action_type == ActionType.USE_REROLL:
                # Remove reroll and roll again - recursive call
                self.game.report(Outcome(OutcomeType.REROLL_USED, team=self.player.team))
                self.rolled = False
                self.step(None)
            else:
                # Player trips
                self.game.move_player(self.player, self.pos)
                KnockDown(self.game, self.player, turnover=True)
                return True

    def available_actions(self):
        return []


class Dodge(Procedure):

    #          0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    success = [6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1]

    @staticmethod
    def dodge_modifiers(game, player, pos):

        modifiers = 1
        tackle_zones_to = game.num_tackle_zones_at(player, pos)

        ignore_opp_mods = False
        if player.has_skill(Skill.STUNTY):
            modifiers = 1
            ignore_opp_mods = True
        if player.has_skill(Skill.TITCHY):
            modifiers -= 1
            ignore_opp_mods = True
        if player.has_skill(Skill.TWO_HEADS):
            modifiers -= 1

        if not ignore_opp_mods:
            modifiers -= tackle_zones_to

        return modifiers

    def __init__(self, game, player, pos, cause_turnover=True):
        super().__init__(game)
        self.player = player
        self.pos = pos
        self.dodge_used = False
        self.awaiting_dodge = False
        self.awaiting_reroll = False
        self.rolled = False
        self.cause_turnover = cause_turnover

    def step(self, action):

        # If player hasn't rolled
        if not self.rolled:

            # Check opp skills
            # tackle_zones, tacklers, prehensile_tailers, diving_tacklers, shadowers, tentaclers =
            # self.game.tackle_zones_in_detailed(self.from_pos)

            # TODO: Allow player to select if shadowing and diving tackle
            # TODO: Put diving tackle or shadowing proc on stack
            # TODO: Auto-use other skills

            # Roll
            roll = DiceRoll([D6()], roll_type=RollType.AGILITY_ROLL)
            self.rolled = True

            # Calculate target
            roll.modifiers = Dodge.dodge_modifiers(self.game, self.player, self.pos)

            # Break tackle - use st instead of ag
            attribute = self.player.get_ag()
            if self.player.has_skill(Skill.BREAK_TACKLE) and self.player.get_st() > self.player.get_st():
                attribute = self.player.get_st()

            roll.target = Dodge.success[attribute]

            if roll.is_d6_success():

                # Success
                self.game.report(Outcome(OutcomeType.SUCCESSFUL_DODGE, player=self.player, pos=self.pos,
                                         rolls=[roll]))
                return True

            else:

                # Fail
                self.game.report(Outcome(OutcomeType.FAILED_DODGE, player=self.player, pos=self.pos, rolls=[roll]))

                # Check if sure feet
                if self.player.has_skill(Skill.DODGE) and not self.dodge_used:
                    self.dodge_used = True
                    self.awaiting_dodge = True
                    self.game.report(Outcome(OutcomeType.SKILL_USED, player=self.player, skill=Skill.DODGE))
                    return False

                # Check if reroll available
                if self.game.state.can_use_reroll(self.player.team) and not self.dodge_used:
                    self.awaiting_reroll = True
                    return False

                # Player trips
                self.game.move_player(self.player, self.pos)
                KnockDown(self.game, self.player, turnover=self.cause_turnover)

                return True

        # If has dodge
        if self.awaiting_dodge:
            self.dodge_used = True
            self.rolled = False
            return self.step(None)

        # If reroll used
        if self.awaiting_reroll:
            if action.action_type == ActionType.USE_REROLL:
                # Remove reroll and roll again - recursive call
                self.game.report(Outcome(OutcomeType.REROLL_USED, team=self.player.team))
                self.player.team.state.use_reroll()
                self.rolled = False
                return self.step(None)
            else:
                # Player trips
                self.game.move_player(self.player, self.pos)
                KnockDown(self.game, self.player, turnover=self.cause_turnover)
                return True

    def available_actions(self):
        if self.awaiting_reroll:
            return [ActionChoice(ActionType.USE_REROLL, team=self.player.team),
                    ActionChoice(ActionType.DONT_USE_REROLL, team=self.player.team)]
        return []


class TurnoverIfPossessionLost(Procedure):

    def __init__(self, game, ball):
        super().__init__(game)
        self.ball = ball

    def step(self, action):
        player_at = self.game.get_player_at(self.ball.position)
        if player_at is None:
            Turnover(self.game)
        elif player_at.team != self.game.get_current_team():
            Turnover(self.game)
        return True

    def available_actions(self):
        return []


class Handoff(Procedure):

    def __init__(self, game, ball, player, pos_to, catcher):
        super().__init__(game)
        self.ball = ball
        self.player = player
        self.pos_to = pos_to
        self.catcher = catcher

    def step(self, action):
        self.ball.move_to(self.pos_to)
        TurnoverIfPossessionLost(self.game, self.ball)
        self.ball.move_to(self.catcher.position)
        Catch(self.game, self.catcher, self.ball, handoff=True)
        self.game.report(Outcome(OutcomeType.HANDOFF, player=self.player, opp_player=self.catcher))
        return True

    def available_actions(self):
        return []


class PassAction(Procedure):

    #          0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    success = [6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1]

    @staticmethod
    def pass_modifiers(game, passer, pass_distance):
        modifiers = Rules.pass_modifiers[pass_distance]
        tackle_zones = game.tackle_zones_in(passer)
        modifiers -= tackle_zones

        # Weather
        if game.state.weather == WeatherType.VERY_SUNNY:
            modifiers -= 1

        if passer.has_skill(Skill.ACCURATE):
            modifiers += 1

        if passer.has_skill(Skill.STRONG_ARM):
            if pass_distance == PassDistance.SHORT_PASS or pass_distance == PassDistance.LONG_PASS or \
                    pass_distance == PassDistance.LONG_BOMB:
                modifiers += 1

        return modifiers

    def __init__(self, game, ball, passer, catcher, pos, pass_distance):
        super().__init__(game)
        self.ball = ball
        self.passer = passer
        self.catcher = catcher
        self.pos = pos
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

            self.ball.carried = False

            # Check for interception
            if not self.interception_tried:
                interceptors = self.game.interceptors(self.passer, self.pos)
                # TODO: Implement option to intercept for all opponent teams
                if len(interceptors) > 0:
                    Interception(self.game, interceptors[0].team, self.ball, interceptors)
                    self.interception_tried = True
                    return False

            # Roll
            self.pass_roll = DiceRoll([D6()], roll_type=RollType.AGILITY_ROLL)
            self.pass_roll.target = Catch.success[self.passer.get_ag()]
            self.pass_roll.modifiers = PassAction.pass_modifiers(self.game, self.passer, self.pass_distance)
            result = self.pass_roll.get_sum()
            mod_result = result + self.pass_roll.modifiers

            if result == 6 or (result != 1 and mod_result >= self.pass_roll.target):
                # Accurate pass
                self.game.report(Outcome(OutcomeType.ACCURATE_PASS, player=self.passer, rolls=[self.pass_roll]))
                self.ball.move_to(self.pos)
                TurnoverIfPossessionLost(self.game, self.ball)
                if self.catcher is not None:
                    Catch(self.game, self.catcher, self.ball, accurate=True)
                else:
                    Bounce(self.game, self.ball)
                return True

            elif result == 1 or mod_result <= 1:
                # Fumble
                self.fumble = True
                self.game.report(Outcome(OutcomeType.FUMBLE, player=self.passer, rolls=[self.pass_roll]))
            else:
                # Inaccurate pass
                self.game.report(Outcome(OutcomeType.INACCURATE_PASS, player=self.passer, rolls=[self.pass_roll]))

            # Check if player has pass
            if self.passer.has_skill(Skill.PASS) and not self.pass_used:
                self.pass_used = True
                self.pass_roll = None
                self.game.report(Outcome(OutcomeType.SKILL_USED, player=self.passer, skill=Skill.PASS))
                self.fumble = False
                return self.step(None)

            # Check if reroll available
            if self.game.can_use_reroll(self.passer.team) and not self.pass_used and not self.reroll_used:
                self.waiting_for_reroll = True
                return False

            # Effect
            if self.fumble:
                Turnover(self.game)
                Bounce(self.game, self.ball)
            else:
                TurnoverIfPossessionLost(self.game, self.ball)
                self.ball.move_to(self.pos)
                Scatter(self.game, self.ball, is_pass=True)

            return True

        # If re-roll used
        if self.waiting_for_reroll:
            if action.action_type == ActionType.USE_REROLL:
                self.reroll_used = True
                self.game.report(Outcome(OutcomeType.REROLL_USED, team=self.passer.team))
                self.passer.team.state.use_reroll()
                self.fumble = False
                self.pass_roll = None
                return self.step(None)
            elif self.fumble:
                Turnover(self.game)
                Bounce(self.game, self.ball)
                return True

            TurnoverIfPossessionLost(self.game, self.ball)
            self.ball.move_to(self.pos)
            Scatter(self.game, self.ball, is_pass=True)
            return True

        return True

    def available_actions(self):

        if self.waiting_for_reroll:
            return [ActionChoice(ActionType.USE_REROLL, team=self.passer.team),
                    ActionChoice(ActionType.DONT_USE_REROLL, team=self.passer.team)]
        return []


class Pickup(Procedure):

    #          0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    success = [6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1]

    @staticmethod
    def pickup_modifiers(game, player):

        modifiers = 1
        tackle_zones = game.num_tackle_zones_in(player)

        if not player.has_skill(Skill.BIG_HAND):
            modifiers -= tackle_zones

        # Weather
        if game.state.weather == WeatherType.POURING_RAIN:
            if not player.has_skill(Skill.BIG_HAND):
                modifiers -= 1

        # Extra arms
        if player.has_skill(Skill.EXTRA_ARMS):
            modifiers += 1

        return modifiers

    def __init__(self, game, ball, player, cause_turnover=True):
        super().__init__(game)
        self.ball = ball
        self.player = player
        self.rolled = False
        self.sure_hands_used = False
        self.waiting_for_reroll = False
        self.waiting_for_sure_hands = False
        self.cause_turnover = cause_turnover

    def step(self, action):

        # Otherwise roll if player hasn't rolled
        if not self.rolled:

            roll = DiceRoll([D6()], roll_type=RollType.AGILITY_ROLL)
            roll.target = Pickup.success[self.player.get_ag()]
            roll.modifiers = Pickup.pickup_modifiers(self.game, self.player)

            # Can player even handle the ball?
            if self.player.has_skill(Skill.NO_HANDS):
                Bounce(self.game, self.ball)
                self.game.report(Outcome(OutcomeType.FAILED_PICKUP, player=self.player))
                return True

            # Roll
            self.rolled = True
            if roll.is_d6_success():
                self.game.report(Outcome(OutcomeType.SUCCESSFUL_PICKUP, player=self.player, rolls=[roll]))
                self.game.set_ball_control(True)
                if self.game.arena.is_touchdown(self.player):
                    Touchdown(self.game, self.player)
                return True
            else:
                self.game.report(Outcome(OutcomeType.FAILED_PICKUP, player=self.player, pos=self.player.position,
                                         rolls=[roll]))
                # Check if sure hands
                if self.player.has_skill(Skill.SURE_HANDS) and not self.sure_hands_used:
                    self.sure_hands_used = True
                    self.waiting_for_sure_hands = True
                    self.game.report(Outcome(OutcomeType.SKILL_USED, player=self.player, pos=self.player.position,
                                             rolls=[roll], skill=Skill.SURE_HANDS))
                    return False

                # Check if reroll available
                if self.game.can_use_reroll(self.player.team) and not self.sure_hands_used:
                    self.waiting_for_reroll = True
                    return False

                # Turnover?
                if self.cause_turnover:
                    Turnover(self.game)

                Bounce(self.game, self.ball)
                self.game.report(Outcome(OutcomeType.FAILED_PICKUP, player=self.player, rolls=[roll]))

                return True

        # If has sure hands
        if self.waiting_for_sure_hands:
            self.sure_hands_used = True
            self.rolled = False
            return self.step(None)

        # If re-roll used
        if self.waiting_for_reroll:
            if action.action_type == ActionType.USE_REROLL:
                self.player.team.state.use_reroll()
                self.game.report(Outcome(OutcomeType.REROLL_USED, team=self.player.team))
                self.rolled = False
                return self.step(None)
            else:
                # Turnover?
                if self.cause_turnover:
                    Turnover(self.game)
                Bounce(self.game, self.ball)

        return True

    def available_actions(self):
        if self.waiting_for_reroll:
            return [ActionChoice(ActionType.USE_REROLL, team=self.player.team),
                    ActionChoice(ActionType.DONT_USE_REROLL, team=self.player.team)]
        return []


class StandUp(Procedure):

    def __init__(self, game, player, roll=False):
        super().__init__(game)
        self.player = player
        self.roll = roll

    def step(self, action):

        if self.roll:
            roll = DiceRoll([D6()], target=4, roll_type=RollType.STAND_UP_ROLL)
            if roll.is_d6_success():
                self.player.state.ready = PlayerReadyState.READY
                self.game.report(Outcome(OutcomeType.PLAYER_STAND_UP_SUCCESS, rolls=[roll], player=self.player))
            else:
                self.player.state.ready = PlayerReadyState.DOWN_USED
                self.game.report(Outcome(OutcomeType.PLAYER_STAND_UP_FAILURE, rolls=[roll], player=self.player))
        else:
            self.player.state.ready = PlayerReadyState.READY

        return True

    def available_actions(self):
        return []


class PlaceBall(Procedure):

    def __init__(self, game, ball):
        super().__init__(game)
        self.ball = ball
        self.aa = [ActionChoice(ActionType.PLACE_BALL, team=self.game.get_kicking_team(),
                                positions=self.game.arena.get_team_side(self.game.get_receiving_team()))]

    def step(self, action):
        if not self.game.arena.is_team_side(action.pos_to, self.game.get_receiving_team()):
            self.ball.move_to(action.pos_to, in_air=True)
            self.game.report(Outcome(OutcomeType.BALL_PLACED, pos=action.pos_to, team=self.game.get_kicking_team()))
        else:
            raise IllegalActionExcpetion("Illegal position")
        return True

    def available_actions(self):
        return self.aa


class EndPlayerTurn(Procedure):

    def __init__(self, game, player):
        super().__init__(game)
        self.player = player

    def step(self, action):
        if self.player.state.ready == PlayerReadyState.READY:
            self.player.state.ready = PlayerReadyState.USED
        elif self.player.state.ready == PlayerReadyState.DOWN_READY:
            self.player.state.ready = PlayerReadyState.DOWN_USED
        self.player.state.moves = 0
        self.game.report(Outcome(OutcomeType.END_PLAYER_TURN, player=self.player))
        self.game.state.active_player = None
        return True

    def available_actions(self):
        return []


class PlayerAction(Procedure):

    def __init__(self, game, player, player_action_type, turn):
        super().__init__(game)
        self.player = player
        self.player_action_type = player_action_type
        self.blitz_block = False
        self.turn = turn
        self.squares = []

    def step(self, action):

        if len(self.squares) == 0:
            self.squares.append(self.player.position)

        if action.action_type == ActionType.END_PLAYER_TURN:
            EndPlayerTurn(self.game, self.player)
            return True

        # Action attributes
        player_to = self.game.get_player(action.player_to_id) if action.player_to_id is not None else None

        if action.action_type == ActionType.STAND_UP:

            StandUp(self.game, self.player, roll=self.player.get_ma() < 3)
            self.player.state.moves += 3
            for i in range(3):
                self.squares.append(self.player.position)

        elif action.action_type == ActionType.MOVE:

            # Check GFI
            gfi = self.player.state.moves + 1 > self.player.get_ma()

            # Check dodge
            dodge = False
            if not self.turn.quick_snap:
                if self.player.has_skill(Skill.BALL_AND_CHAIN):
                    # Ball and chain -> Auto-dodge
                    dodge = True
                    gfi = False
                else:
                    tackle_zones_from = self.game.num_tackle_zones_in(self.player)
                    dodge = tackle_zones_from > 0

            # Add proc
            Move(self.game, self.player, action.pos_to, gfi, dodge)
            self.squares.append(action.pos_to)

            self.player.state.moves += 1

            return False

        elif action.action_type == ActionType.BLOCK:

            # Check GFI
            gfi = False
            if self.player_action_type == PlayerActionType.BLITZ:
                move_needed = 3 if self.player.state.ready == PlayerReadyState.DOWN_READY else 1
                gfi = self.player.state.moves + move_needed > self.player.get_ma()
                # Use movement
                self.player.state.moves += move_needed
                for i in range(move_needed):
                    self.squares.append(self.player.position)
                    self.player.state.ready = PlayerReadyState.READY

            # Check frenzy
            '''
            if self.player_from.has_skill(Skill.FRENZY):
                move_needed = 0
                if self.player_action_type == ActionType.BLITZ:
                    move_needed = 1
                gfi_allowed = 3 if self.player_from.has_skill(Skill.SPRINT) else 2
                if player_state_from.moves + move_needed <= self.player_from.get_ma() + gfi_allowed:
                    gfi_2 = player_state_from.moves + move_needed > self.player_from.get_ma()
                    Block(self.game, self.team, self.player_from, player_to, action.pos_to, gfi=gfi)
                    gfi = gfi_2  # Switch gfi
                # Use movement
                player_state_from.moves += move_needed
            '''

            # End turn after block - if not a blitz action
            if self.player_action_type == PlayerActionType.BLOCK:
                EndPlayerTurn(self.game, self.player)

            # Block
            Block(self.game, self.player, player_to, gfi=gfi)
            self.blitz_block = True if self.player_action_type == PlayerActionType.BLITZ else False

            if self.player_action_type == PlayerActionType.BLOCK:
                return True

            return False

        elif action.action_type == ActionType.FOUL:

            EndPlayerTurn(self.game, self.player)
            Foul(self.game, self.player, player_to)

            return True

        elif action.action_type == ActionType.HANDOFF:

            EndPlayerTurn(self.game, self.player)
            Handoff(self.game, self.game.get_ball_at(self.player), self.player, action.pos_to,
                    self.game.get_player_at(action.pos_to))

            return True

        elif action.action_type == ActionType.PASS:

            # Check distance
            pass_distance = self.game.pass_distance(self.player, action.pos_to)
            EndPlayerTurn(self.game, self.player)
            PassAction(self.game, self.game.get_ball_at(self.player), self.player, player_to, action.pos_to,
                       pass_distance)
            self.turn.pass_available = False

            return True

    def available_actions(self):
        actions = []

        # Move actions
        if self.player_action_type != PlayerActionType.BLOCK:
            move_positions = []
            agi_rolls = []
            move_needed = 1 if self.player.state.ready == PlayerReadyState.DOWN_READY else 1
            gfi = self.player.state.moves + move_needed > self.player.get_ma()
            sprints = 3 if self.player.has_skill(Skill.SPRINT) else 2
            if self.player.state.ready is PlayerReadyState.DOWN_READY:
                if self.player.get_ma() < 3:
                    agi_rolls.append([4])
                else:
                    agi_rolls.append([])
                actions.append(ActionChoice(ActionType.STAND_UP, players=[self.player],
                                            positions=[self.player.position], team=self.player.team,
                                            agi_rolls=agi_rolls))
                # TODO: Check if position is necessary here? ^^
            elif (not self.turn.quick_snap
                  and self.player.state.moves + move_needed <= self.player.get_ma() + sprints) \
                    or (self.turn.quick_snap and self.player.state.moves == 0):
                for square in self.game.adjacent_squares(self.player.position, exclude_occupied=True):
                    ball_at = self.game.get_ball_at(square) is not None and not self.game.is_ball_in_air()
                    move_positions.append(square)
                    rolls = []
                    if not self.turn.quick_snap:
                        if gfi:
                            rolls.append(2)
                        if self.game.tackle_zones_in(self.player.position) > 0:
                            modifiers = Dodge.dodge_modifiers(self.game, self.player, square)
                            target = Dodge.success[self.player.get_ag()]
                            rolls.append(min(6, max(2, target - modifiers)))
                        if ball_at:
                            target = Pickup.success[self.player.get_ag()]
                            modifiers = Pickup.pickup_modifiers(self.game, self.player)
                            rolls.append(min(6, max(2, target - modifiers)))
                    agi_rolls.append(rolls)
                if len(move_positions) > 0:
                    actions.append(ActionChoice(ActionType.MOVE, players=[self.player], team=self.player.team,
                                                positions=move_positions, agi_rolls=agi_rolls))

        # Block actions
        if self.player_action_type == PlayerActionType.BLOCK or (self.player_action_type == PlayerActionType.BLITZ
                                                                 and not self.blitz_block):

            # Check movement left if blitz,
            can_block = True
            gfi = False
            if self.player_action_type == PlayerActionType.BLITZ:
                move_needed = 3 if self.player.state.ready == PlayerReadyState.DOWN_READY else 1
                gfi_allowed = 3 if self.player.has_skill(Skill.SPRINT) else 2
                if self.player.state.moves + move_needed > self.player.get_ma() + gfi_allowed or move_needed > 1:
                    can_block = False
                gfi = self.player.state.moves + move_needed > self.player.get_ma()

            # Find adjacent enemies to block
            if can_block:
                block_positions = []
                block_rolls = []
                for square in self.game.adjacent_player_squares(self.player.position,
                                                                include_team=not self.player.team,
                                                                include_away=self.player.team,
                                                                only_blockable=True):
                    player_to = self.game.get_player_at(square)
                    block_positions.append(square)
                    dice, favor = Block.dice_and_favor(self.game, attacker=self.player, defender=player_to,
                                                       blitz=self.player_action_type == PlayerActionType.BLITZ,
                                                       dauntless_success=False)
                    if favor != self.player.team:
                        dice *= -1
                    block_rolls.append(dice)
                if len(block_positions) > 0:
                    agi_rolls = [([2] if gfi else []) for _ in block_positions]
                    actions.append(ActionChoice(ActionType.BLOCK, players=[self.player], team=self.player.team,
                                                positions=block_positions, block_rolls=block_rolls,
                                                agi_rolls=agi_rolls))

        # Foul actions
        if self.player_action_type == PlayerActionType.FOUL:
            foul_positions = []
            foul_rolls = []
            for square in self.game.adjacent_player_squares(self.player.position, include_own=False,
                                                            include_opp=True,
                                                            only_foulable=True):
                player_to = self.game.get_player_at(square)
                foul_positions.append(square)
                armor = player_to.get_av()
                assists_from = self.game.assists(self.player, player_to, ignore_guard=True)
                assists_to = self.game.assists(player_to, self.player, ignore_guard=True)
                foul_rolls.append(min(0, armor + 1 - len(assists_from) + len(assists_to)))

            if len(foul_positions) > 0:
                actions.append(ActionChoice(ActionType.FOUL, players=[self.player], team=self.player.team,
                                            positions=foul_positions, block_rolls=foul_rolls))

        # Handoff actions
        if self.player_action_type == PlayerActionType.HANDOFF and self.game.has_ball(self.player):
            hand_off_positions = []
            agi_rolls = []
            for square in self.game.adjacent_player_squares(self.player.position, include_own=True, include_opp=False):
                player_to = self.game.get_player_at(square)
                if player_to.state.ready in Rules.catchable and Skill.NO_HANDS not in player_to.get_skills():
                    hand_off_positions.append(square)
                    modifiers = Catch.catch_modifiers(self.game, self.player, square)
                    target = Catch.success[self.player.get_ag()]
                    agi_rolls.append([min(6, max(2, target - modifiers))])

            if len(hand_off_positions) > 0:
                actions.append(ActionChoice(ActionType.HANDOFF, players=[self.player], team=self.player.team,
                                            positions=hand_off_positions, agi_rolls=agi_rolls))

        # Pass actions
        if self.player_action_type == PlayerActionType.PASS and self.game.has_ball(self.player):
            positions, distances = self.game.passes(self.player, self.player.position)
            agi_rolls = []
            cache = {}
            for i in range(len(distances)):
                distance = distances[i]
                position = positions[i]
                if distance not in cache:
                    modifiers = PassAction.pass_modifiers(self.game, self.player, distance)
                    target = PassAction.success[self.player.get_ag()]
                    cache[distance] = min(6, max(2, target - modifiers))
                rolls = [cache[distance]]
                player_to = self.game.get_player_at(position)
                if player_to is not None and player_to.team == self.player.team \
                        and player_to.state.ready in Rules.catchable:
                    catch_target = Catch.success[player_to.get_ag()]
                    catch_modifiers = Catch.catch_modifiers(self.game, player_to, accurate=True)
                    rolls.append(min(6, max(2, catch_target - catch_modifiers)))
                agi_rolls.append(rolls)
            if len(positions) > 0:
                actions.append(ActionChoice(ActionType.PASS, players=[self.player], team=self.player.team,
                                            positions=positions, agi_rolls=agi_rolls))

        actions.append(ActionChoice(ActionType.END_PLAYER_TURN, players=[self.player], team=self.player.team))
        return actions


class StartGame(Procedure):

    def __init__(self, game):
        super().__init__(game)

    def step(self, action):
        for player in self.game.team.players:
            self.game.state.team_dugout.reserves.append(player.player_id)
        for player in self.game.away.players:
            self.game.state.away_dugout.reserves.append(player.player_id)
        self.game.report(Outcome(OutcomeType.GAME_STARTED))
        return True

    def available_actions(self):
        return [ActionChoice(ActionType.START_GAME, team=None)]


class EndGame(Procedure):

    def __init__(self, game):
        super().__init__(game)

    def step(self, action):
        self.game.state.team_turn = None
        self.game.game_over = True

    def available_actions(self):
        return []


class Pregame(Procedure):

    def __init__(self, game):
        super().__init__(game)
        CoinToss(self.game)
        # self.game.stack.push(Inducements(self.game, True))
        # self.game.stack.push(Inducements(self.game, False))
        # self.game.stack.push(GoldToPettyCash(self.game))
        WeatherTable(self.game)
        Fans(self.game)
        StartGame(self.game)

    def step(self, action):
        Half(self.game, 2)
        Half(self.game, 1)
        self.game.set_half(1)
        self.game.set_team_turn(True, 0)
        self.game.set_team_turn(False, 0)
        return True

    def available_actions(self):
        return []


class PreHalf(Procedure):

    def __init__(self, game, team):
        super().__init__(game)
        self.team = team
        self.checked = []

    def step(self, action):
        for player_id, player_state in self.game.state.get_team_state(self.team).player_states.items():
            if player_state.player_ready_state == PlayerReadyState.KOD and player_id not in self.checked:
                roll = DiceRoll([D6()], roll_type=RollType.KO_READY_ROLL)
                player = self.game.get_player(player_id)
                if roll.get_sum() >= 4:
                    self.game.kod_to_reserves(player, self.team)
                    self.checked.append(player_id)
                    self.game.report(Outcome(OutcomeType.PLAYER_READY, player=player, rolls=[roll]))
                    return False
                self.checked.append(player_id)
                self.game.report(Outcome(OutcomeType.PLAYER_NOT_READY, player=player, rolls=[roll]))
                return False
        self.game.state.reset_kickoff()
        return True

    def available_actions(self):
        return []


class FollowUp(Procedure):

    def __init__(self, game, player, pos_to):
        super().__init__(game)
        self.player = player
        self.pos_from = self.game.get_player_position(player)
        self.pos_to = pos_to

    def step(self, action):

        if action.pos_to == self.pos_to:
            self.game.move_player(self.player, self.pos_to)
            self.game.report(Outcome(OutcomeType.FOLLOW_UP, pos=self.pos_to, player=self.player))

        return True

    def available_actions(self):
        if not self.player.has_skill(Skill.FRENZY):
            return [ActionChoice(ActionType.SELECT_SQUARE, team=self.player.team,
                                 positions=[self.pos_from, self.pos_to], players=[self.player])]
        else:
            return [ActionChoice(ActionType.SELECT_SQUARE, team=self.player.team, positions=[self.pos_to],
                                 players=[self.player])]


class Push(Procedure):

    def __init__(self, game, pusher, player, knock_down=False, blitz=False, chain=False):
        super().__init__(game)
        self.pusher = pusher
        self.player = player
        self.knock_down = knock_down
        self.blitz = blitz
        self.waiting_stand_firm = False
        self.stand_firm_used = False
        self.chain = chain
        self.waiting_for_move = False
        self.player_chain = None
        self.push_to = None
        self.follow_to = None
        self.squares = None
        self.crowd = False

    def step(self, action):

        # When proceeding pushes are over, move player(s)
        if self.waiting_for_move:

            # Move pushed player
            self.game.move_player(self.player, self.push_to)

            # Ball
            if self.game.has_ball(self.player):
                if self.game.is_touchdown(self.player):
                    Touchdown(self.game, self.player)
            elif self.game.get_ball_at(self.push_to) is not None:
                Bounce(self.game, self.game.get_ball_at(self.push_to))

            # Knock down
            if self.knock_down or self.crowd:
                KnockDown(self.game, self.player, in_crowd=self.crowd, armor_roll=not self.crowd)

            # Chain push
            if not self.chain:
                FollowUp(self.game, self.pusher, self.follow_to)

            return True

        # Use stand firm
        if self.waiting_stand_firm:
            if action.action_type == ActionType.USE_STAND_FIRM:
                if self.player.team.team_id != action.team_id:
                    raise IllegalActionExcpetion("Must be the owner of the player to use the stand firm skill.")
                return True
            else:
                self.waiting_stand_firm = False
                self.stand_firm_used = True

        # Get possible squares
        if self.squares is None:
            self.squares = self.game.push_squares(self.pusher.position, self.player.position)
            return False

        # Stand firm
        if self.player.has_skill(Skill.STAND_FIRM) and not self.stand_firm_used:
            if not (self.blitz and self.pusher.has_skill(Skill.JUGGERNAUT)):
                self.waiting_stand_firm = True
                return False

        if action.action_type == ActionType.SELECT_SQUARE:

            # Push to crowd?
            self.crowd = self.game.is_out_of_bounds(action.pos_to)

            # Report
            if self.crowd:
                self.game.report(Outcome(OutcomeType.PUSHED_INTO_CROWD, player=self.player))
            else:
                self.game.report(Outcome(OutcomeType.PUSHED, player=self.player, pos=action.pos_to))

            # Follow up - wait if push is delayed
            player_at = self.game.get_player_at(action.pos_to)

            # Move players in next step - after chaining
            self.waiting_for_move = True
            self.squares = None

            # Save positions before chaining
            self.push_to = Square(action.pos_to.x, action.pos_to.y)
            pos_to = self.game.get_player_position(self.player)
            self.follow_to = Square(pos_to.x, pos_to.y)

            # Chain push
            if player_at is not None:
                self.player_chain = player_at
                Push(self.game, self.player, self.player_chain, knock_down=False, chain=True)

            return False

        raise Exception("Unknown push sequence")

    def available_actions(self):
        actions = []
        if self.squares is not None:
            if self.player.has_skill(Skill.SIDE_STEP):
                actions.append(ActionChoice(ActionType.SELECT_SQUARE, team=self.player.team, positions=self.squares))
            else:
                actions.append(ActionChoice(ActionType.SELECT_SQUARE, team=self.pusher.team, positions=self.squares))
        return actions


class Scatter(Procedure):

    def __init__(self, game, ball, kick=False, is_pass=False, gentle_gust=False):
        super().__init__(game)
        self.ball = ball
        self.kick = kick
        self.is_pass = is_pass
        self.gentle_gust = gentle_gust

    def step(self, action):

        # Don't scatter if ball is out
        if self.game.is_out_of_bounds(self.ball.position):
            return True

        n = 3 if self.is_pass else 1
        rolls = [DiceRoll([D8()], roll_type=RollType.SCATTER_ROLL) for _ in range(n)]

        for s in range(n):

            # Roll
            roll_scatter = rolls[s]
            if self.kick and not self.gentle_gust:
                roll_distance = DiceRoll([D6()], roll_type=RollType.DISTANCE_ROLL)
                rolls += [roll_distance]

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
            distance = 1 if not self.kick or self.gentle_gust else roll_distance.get_sum()

            for i in range(distance):
                # Move ball on square
                self.ball.move(x, y)

                if self.kick and i == 0:
                    self.game.report(Outcome(OutcomeType.BALL_SCATTER, rolls=rolls))

                # Check out of bounds
                if self.kick:
                    if self.game.is_ball_out():
                        if self.gentle_gust:
                            # Touchback will be enforced after kick-off table when ball lands
                            self.game.report(Outcome(OutcomeType.GENTLE_GUST_OUT_OF_BOUNDS, pos=self.ball.position,
                                                     rolls=rolls))
                        else:
                            # Touchback will be enforced after kick-off table when ball lands
                            self.game.report(Outcome(OutcomeType.KICK_OUT_OF_BOUNDS, pos=self.ball.position,
                                                     rolls=rolls))
                        return True
                    elif self.game.arena.is_team_side(self.ball.position, self.game.get_kicking_team()):
                        if self.gentle_gust:
                            # Touchback will be enforced after kick-off table when ball lands
                            self.game.report(Outcome(OutcomeType.GENTLE_GUST_OPP_HALF, pos=self.ball.position,
                                                     rolls=rolls))
                        else:
                            # Touchback will be enforced after kick-off table when ball lands
                            self.game.report(Outcome(OutcomeType.KICK_OPP_HALF, pos=self.ball.position, rolls=rolls))
                        return True
                else:
                    # Throw in
                    if self.game.is_ball_out():
                        # Move ball back
                        self.game.move_ball(-x, -y)
                        ThrowIn(self.game, self.ball.position)
                        self.game.report(Outcome(OutcomeType.BALL_SCATTER, rolls=rolls))
                        self.game.report(Outcome(OutcomeType.BALL_OUT_OF_BOUNDS,
                                                 pos=self.ball.position))
                        return True

                    # Passes are scattered three times
                    if self.is_pass and s < n-1:
                        continue

                    self.game.report(Outcome(OutcomeType.BALL_SCATTER, rolls=rolls))

                    # On player -> Catch
                    player = self.game.get_player_at(self.ball.position)
                    if player is not None:
                        Catch(self.game, player, self.ball)
                        self.game.report(Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.ball.position,
                                                 player=player, rolls=[roll_scatter]))
                        return True

        if self.kick:
            if self.gentle_gust:
                # Wait for ball to land
                self.game.report(Outcome(OutcomeType.GENTLE_GUST_IN_BOUNDS, pos=self.ball.position,
                                         rolls=[roll_scatter]))
            else:
                # Wait for ball to land
                self.game.report(Outcome(OutcomeType.KICK_IN_BOUNDS, pos=self.ball.position,
                                         rolls=[roll_scatter, roll_distance]))
        else:
            # Bounce ball
            Bounce(self.game, self.ball)

        return True

    def available_actions(self):
        return []


class ClearBoard(Procedure):

    def __init__(self, game):
        super().__init__(game)

    def step(self, action):
        self.game.remove_ball()
        for team in self.game.teams:
            for player in team.players:
                # If player not in reserves. move it to it
                if self.game.get_player_position(player) is not None:
                    # Set to ready
                    player.state.ready = PlayerReadyState.READY
                    # Remove from pitch
                    self.game.pitch_to_reserves(player)
                    # Check if heat exhausted
                    if self.game.state.weather == WeatherType.SWELTERING_HEAT:
                        roll = DiceRoll([D6()], roll_type=RollType.SWELTERING_HEAT_ROLL)
                        if roll.get_sum() == 1:
                            player.state.ready = PlayerReadyState.HEATED
                            self.game.report(Outcome(OutcomeType.PLAYER_HEATED, player=player, rolls=[roll]))
                        else:
                            self.game.report(Outcome(OutcomeType.PLAYER_NOT_HEATED, player=player, rolls=[roll]))
        return True

    def available_actions(self):
        return []


class Setup(Procedure):

    def __init__(self, game, team, reorganize=False):
        super().__init__(game)
        self.team = team
        self.reorganize = reorganize
        self.selected_player = None
        if self.reorganize:
            positions = game.arena.get_team_side(team)
        else:
            positions = game.arena.get_team_side(team) + [None]
        self.aa = [
            ActionChoice(ActionType.PLACE_PLAYER, team=team,
                         players=game.get_players_on_pitch(team) if self.reorganize else team.players,
                         positions=positions),
            ActionChoice(ActionType.END_SETUP, team=team)
        ]
        if not self.reorganize:
            self.aa.append(ActionChoice(ActionType.AUTO, team=team))

    def step(self, action):

        if action.action_type == ActionType.AUTO:
            for i in range(min(11, len(self.game.get_reserves(self.team)))):
                player_id = self.game.get_reserves(self.team)[0]
                y = 3
                x = 13 if self.team else 14
                self.step(Action(ActionType.PLACE_PLAYER, player_from_id=player_id, pos_from=None,
                                 pos_to=Square(x, y+i)))
                if i == 11:
                    self.step(Action(ActionType.END_SETUP))
                    break
            return True

        if action.action_type == ActionType.END_SETUP:
            if not self.game.state.pitch.is_setup_legal(self.team, max_players=self.game.config.pitch_max,
                                                        min_players=self.game.config.pitch_min):
                self.game.report(Outcome(OutcomeType.ILLEGAL_SETUP_NUM, team=self.team))
                return False
            elif not self.game.state.pitch.is_setup_legal_scrimmage(self.team,
                                                                    min_players=self.game.config.scrimmage_max):
                self.game.report(Outcome(OutcomeType.ILLEGAL_SETUP_SCRIMMAGE, team=self.team))
                return False
            elif not self.game.state.pitch.is_setup_legal_wings(self.team, max_players=self.game.config.wing_max):
                self.game.report(Outcome(OutcomeType.ILLEGAL_SETUP_WINGS, team=self.team))
                return False
            self.game.report(Outcome(OutcomeType.SETUP_DONE, team=self.team))
            return True

        if action.action_type == ActionType.PLACE_PLAYER:
            player = self.game.get_player(action.player_from_id)
            if action.pos_from is None and action.pos_to is None:
                # Move player from reserve to reserve - sure
                return False
            if action.pos_to is None:
                self.game.pitch_to_reserves(player)
            elif action.pos_from is None:
                self.game.reserves_to_pitch(player, action.pos_to)
            self.game.report(Outcome(OutcomeType.PLAYER_PLACED, pos=action.pos_to, player=action.player_from_id))
            return False

    def available_actions(self):
        return self.aa


class ThrowIn(Procedure):

    def __init__(self, game, ball):
        super().__init__(game)
        self.ball = ball

    def step(self, action):

        # Roll
        roll_direction = DiceRoll([D3()], roll_type=RollType.SCATTER_ROLL)
        roll_distance = DiceRoll([D6(), D6()], roll_type=RollType.DISTANCE_ROLL)

        # Scatter
        x = 0
        y = 0

        if self.ball.position.y == 1 and self.ball.position.x == 1:  # Top left corner
            y = 0 if roll_direction.get_sum() == 1 else 1
            x = 0 if roll_direction.get_sum() == 3 else 1
        elif self.ball.position.y == 1 and self.ball.position.x == len(self.game.arena.board[0])-2:  # Top right corner
            y = 0 if roll_direction.get_sum() == 3 else 1
            x = 0 if roll_direction.get_sum() == 1 else -1
        elif self.ball.position.y == len(self.game.arena.board)-2 and self.ball.position.x == len(self.game.arena.board[0])-2:  # Bottom right corner
            y = 0 if roll_direction.get_sum() == 1 else -1
            x = 0 if roll_direction.get_sum() == 3 else -1
        elif self.ball.position.y == len(self.game.arena.board)-2 and self.ball.position.x == 1:  # Bottom left corner
            y = 0 if roll_direction.get_sum() == 3 else -1
            x = 0 if roll_direction.get_sum() == 1 else 1
        elif self.ball.position.y == 1:  # Above
            y = 1
            x = -1 if roll_direction.get_sum() == 3 else 1
        elif self.ball.position.y == len(self.game.arena.board)-2:  # Below
            y = -1
            x = -1 if roll_direction.get_sum() == 1 else 1
        elif self.ball.position.x == 1:  # Right
            x = 1
            y = -1 if roll_direction.get_sum() == 3 else 1
        elif self.ball.position.x == len(self.game.arena.board[0])-2:  # Left
            x = -1
            y = -1 if roll_direction.get_sum() == 1 else 1

        for i in range(roll_distance.get_sum()):
            self.ball.move(x, y)
            if self.game.is_out_of_bounds(self.ball):
                self.ball.move(-x, -y)
                ThrowIn(self.game, self.ball)
                self.game.report(Outcome(OutcomeType.THROW_IN_OUT_OF_BOUNDS, pos=self.ball.position,
                                         rolls=[roll_direction, roll_distance]))
                return True

        self.game.report(Outcome(OutcomeType.THROW_IN, pos=self.ball.position, rolls=[roll_direction,  roll_distance]))

        # On player -> Catch
        player = self.game.get_player_at(self.ball.position)
        if player is not None:
            Catch(self.game, player, self.ball)

        return True

    def available_actions(self):
        return []


class Turnover(Procedure):

    def __init__(self, game):
        super().__init__(game)

    def step(self, action):
        self.game.report(Outcome(OutcomeType.TURNOVER, team=self.game.state.current_team))
        self.game.state.active_player = None
        EndTurn(self.game)
        return True

    def available_actions(self):
        return []


class Touchdown(Procedure):

    def __init__(self, game, player):
        super().__init__(game)
        self.game = game
        self.player = player

    def step(self, action):
        self.game.report(Outcome(OutcomeType.TOUCHDOWN, team=self.player.team, player=self.player))
        self.player.team.state.score += 1

        # Scoring in opponents turn
        if self.player.team != self.game.state.current_team:
            if self.game.get_team_turn(self.player.team) < 8:
                EndTurn(self.game, kickoff=True)
            EndTurn(self.game, kickoff=False)
        else:
            # Prepare for next kickoff
            self.game.state.kicking_team_this_drive = self.player.team
            self.game.state.receiving_team_this_drive = self.game.get_opp_team(self.player.team)
            EndTurn(self.game, kickoff=self.player.team.state.turn < 8)

        return True

    def available_actions(self):
        return []


class TurnStunned(Procedure):

    def __init__(self, game, team):
        super().__init__(game)
        self.team = team

    def step(self, action):
        players = []
        for player in self.team.players:
            if player.ready == PlayerReadyState.STUNNED:
                player.state.ready = PlayerReadyState.DOWN_USED
                players.append(player)
        self.game.report(Outcome(OutcomeType.STUNNED_TURNED))
        return True

    def available_actions(self):
        return []


class ResetTurn(Procedure):

    def __init__(self, game, team):
        super().__init__(game)
        self.team = team

    def step(self, action):
        self.game.reset_turn(self.team)
        return True

    def available_actions(self):
        return []


class EndTurn(Procedure):

    def __init__(self, game, kickoff=False):
        super().__init__(game)
        self.kickoff = kickoff

    def step(self, action):

        # Remove all procs in the current turn - including the current turn proc.
        x = 0
        for i in reversed(range(self.game.stack.size())):
            x += 1
            if isinstance(self.game.stack.items[i], Turn):
                break
        for i in range(x):
            self.game.stack.pop()

        # Add kickoff procedure - if there are more turns left
        if self.kickoff and not self.game.is_last_turn():
            KickOff(self.game)
            # Setup in turn order from after scoring team
            before = []
            after = []
            added = False
            for t in self.game.get_turn_order():
                if added:
                    after.append(t)
                else:
                    before.append(t)
                if t == self.game.get_current_team():
                    added = True
            for team in reversed(after+before):
                Setup(self.game, team)
            ClearBoard(self.game)

    def available_actions(self):
        return []


class Turn(Procedure):

    def __init__(self, game, team, half, turn, blitz=False, quick_snap=False):
        super().__init__(game)
        self.team = team
        self.half = half
        self.turn = turn
        self.blitz = blitz
        self.started = False
        self.quick_snap = quick_snap
        self.blitz_available = not quick_snap
        self.pass_available = not quick_snap
        self.handoff_available = not quick_snap
        self.foul_available = not quick_snap

    def start_player_action(self, outcome_type, player_action_type, player):

        # Start action
        self.game.state.active_player_id = player.player_id
        PlayerAction(self.game, player, player_action_type, turn=self)
        self.game.report(Outcome(outcome_type, player=player))

    def step(self, action):

        # Update state
        if not self.started:
            self.started = True
            self.game.state.team_turn = self.team
            if not self.blitz and not self.quick_snap:
                TurnStunned(self.game, self.team)
                ResetTurn(self.game, self.team)
                self.game.report(Outcome(OutcomeType.TURN_START, team=self.team,
                                         n=self.game.state.team_state.turn))
                self.game.state.get_team_state(self.team).turn = self.turn

        # Handle End Turn action
        if action.action_type == ActionType.END_TURN:
            if self.blitz:
                self.game.report(Outcome(OutcomeType.END_OF_BLITZ, team=self.team))
            elif self.quick_snap:
                self.game.report(Outcome(OutcomeType.END_OF_QUICK_SNAP, team=self.team))
            else:
                self.game.report(Outcome(OutcomeType.END_OF_TURN, team=self.team))
            self.game.state.active_player_id = None
            return True

        # Start movement action
        player = self.game.get_player(action.player_from_id)
        if action.action_type == ActionType.START_MOVE:
            self.start_player_action(OutcomeType.MOVE_ACTION_STARTED, PlayerActionType.MOVE, player)
            return False

        # Start blitz action
        if action.action_type == ActionType.START_BLITZ:
            self.blitz_available = False
            self.start_player_action(OutcomeType.BLITZ_ACTION_STARTED, PlayerActionType.BLITZ, player)
            return False

        # Start foul action
        if action.action_type == ActionType.START_FOUL:
            self.foul_available = False
            self.start_player_action(OutcomeType.FOUL_ACTION_STARTED, PlayerActionType.FOUL, player)
            return False

        # Start block action
        if action.action_type == ActionType.START_BLOCK:
            self.start_player_action(OutcomeType.BLOCK_ACTION_STARTED, PlayerActionType.BLOCK, player)
            return False

        # Start pass action
        if action.action_type == ActionType.START_PASS:
            self.pass_available = False
            self.start_player_action(OutcomeType.PASS_ACTION_STARTED, PlayerActionType.PASS, player)
            return False

        # Start handoff action
        if action.action_type == ActionType.START_HANDOFF:
            self.handoff_available = False
            self.start_player_action(OutcomeType.HANDOFF_ACTION_STARTED, PlayerActionType.HANDOFF, player)
            return False

    def available_actions(self):
        move_players = []
        block_players = []
        blitz_players = []
        pass_players = []
        handoff_players = []
        foul_players = []
        for player in self.game.get_players_on_pitch(self.team):
            if self.blitz:
                if self.game.num_tackle_zones_in(player) > 0:
                    continue
            if player.state.ready == PlayerReadyState.READY or player.state.ready == PlayerReadyState.DOWN_READY:
                move_players.append(player)
                if self.blitz_available:
                    blitz_players.append(player)
                if self.pass_available:
                    pass_players.append(player)
                if self.handoff_available:
                    handoff_players.append(player)
                if self.foul_available:
                    foul_players.append(player)
            if player.state.ready == PlayerReadyState.READY and not self.quick_snap and not self.blitz:
                block_players.append(player)

        actions = []
        if len(move_players) > 0:
            actions.append(ActionChoice(ActionType.START_MOVE, team=self.team, players=move_players))
        if len(block_players) > 0:
            actions.append(ActionChoice(ActionType.START_BLOCK, team=self.team, players=block_players))
        if len(blitz_players) > 0:
            actions.append(ActionChoice(ActionType.START_BLITZ, team=self.team, players=blitz_players))
        if len(pass_players) > 0:
            actions.append(ActionChoice(ActionType.START_PASS, team=self.team, players=pass_players))
        if len(handoff_players) > 0:
            actions.append(ActionChoice(ActionType.START_HANDOFF, team=self.team, players=handoff_players))
        if len(foul_players) > 0:
            actions.append(ActionChoice(ActionType.START_FOUL, team=self.team, players=foul_players))
        actions.append(ActionChoice(ActionType.END_TURN, team=self.team))

        return actions


class WeatherTable(Procedure):

    def __init__(self, game, kickoff=False):
        super().__init__(game)
        self.kickoff = kickoff

    def step(self, action):
        roll = DiceRoll([D6(), D6()], roll_type=RollType.WEATHER_ROLL)
        if roll.get_sum() == 2:
            self.game.state.weather = WeatherType.SWELTERING_HEAT
            self.game.report(Outcome(OutcomeType.WEATHER_SWELTERING_HEAT, rolls=[roll]))
        if roll.get_sum() == 3:
            self.game.state.weather = WeatherType.VERY_SUNNY
            self.game.report(Outcome(OutcomeType.WEATHER_VERY_SUNNY, rolls=[roll]))
        if 4 <= roll.get_sum() <= 10:
            if self.kickoff and self.game.state.weather == WeatherType.NICE:
                self.game.state.gentle_gust = True
            self.game.state.weather = WeatherType.NICE
            self.game.report(Outcome(OutcomeType.WEATHER_NICE, rolls=[roll]))
        if roll.get_sum() == 11:
            self.game.state.weather = WeatherType.POURING_RAIN
            self.game.report(Outcome(OutcomeType.WEATHER_POURING_RAIN, rolls=[roll]))
        if roll.get_sum() == 12:
            self.game.state.weather = WeatherType.BLIZZARD
            self.game.report(Outcome(OutcomeType.WEATHER_BLIZZARD, rolls=[roll]))
        return True

    def available_actions(self):
        return []
