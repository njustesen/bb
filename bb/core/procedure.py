import random
from bb.core.model import *
from bb.core.table import *
from bb.core.exception import *


class Procedure():

    def __init__(self, game):
        self.game = game
        self.game.stack.push(self)
        self.done = False

    def step(self, action):
        pass

    def available_actions(self):
        pass


class Apothecary(Procedure):

    def __init__(self, game, home, player_id, roll, outcome, opp_player_id, casualty=None, effect=None):
        super().__init__(game)
        self.game = game
        self.home = home
        self.player_id = player_id
        self.opp_player_id = opp_player_id
        self.player = game.get_player(player_id)
        self.opp_player = game.get_player(opp_player_id)
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
                self.game.state.field.remove(self.player_id)
                self.game.state.get_dugout(self.home).reserves.append(self.player_id)
                self.game.report(Outcome(OutcomeType.APOTHECARY_USED_KO, player_id=self.player_id, team_home=self.home))

            else:

                # Player is KO
                self.game.state.field.remove(self.player_id)
                self.game.state.get_dugout(self.home).kod.append(self.player_id)
                self.game.state.get_team_state(self.home).player_states[self.player_id] = PlayerState.KOD
                self.game.report(Outcome(OutcomeType.APOTHECARY_USED_KO, player_id=self.player_id, team_home=self.home))

            return True

        elif self.outcome == OutcomeType.CASUALTY:

            if action.action_type == ActionType.USE_APOTHECARY:

                self.roll_second = DiceRoll([D6(), D8()])
                result = self.roll_second.get_sum()
                n = min(61, max(38, result))
                self.casualty_second = CasualtyType(n)
                self.effect_second = Rules.casualty_effect[self.casualty_second]
                self.game.state.get_team_state(self.home).apothecary_available = False
                self.game.report(Outcome(OutcomeType.CASUALTY_APOTHECARY, player_id=self.player_id, team_home=self.home, rolls=[self.roll_first, self.roll_second]))
                self.waiting_apothecary = True

                return False

            if action.action_type == ActionType.SELECT_ROLL:

                effect = self.effect_first if action.idx == 0 else self.effect_second
                casualty = self.casualty_first if action.idx == 0 else self.casualty_second
                roll = self.roll_first if action.idx == 0 else self.roll_second

                # Apply casualty
                if effect == CasualtyEffect.NONE:
                    self.game.state.get_team_state(self.home).player_states[self.player_id] = PlayerState.BH
                elif effect in Casualty.miss_next_game:
                    self.game.state.get_team_state(self.home).player_states[self.player_id] = PlayerState.MNG
                elif effect == CasualtyEffect.DEAD:
                    self.game.state.get_team_state(self.home).player_states[self.player_id] = PlayerState.DEAD

                self.game.state.field.remove(self.player_id)

                if effect != CasualtyEffect.NONE:
                    self.game.state.get_team_state(self.home).injure_player(self.player_id, effect)
                    self.game.state.get_dugout(self.home).casualties.append(self.player_id)
                else:
                    # Apothecary puts badly hurt players in the reserves
                    self.game.state.get_dugout(self.home).reserves.append(self.player_id)

                self.game.report(Outcome(OutcomeType.CASUALTY, player_id=self.player_id, team_home=self.home, n=effect.name, rolls=[roll]))

        return True

    def available_actions(self):
        if self.outcome == OutcomeType.KNOCKED_OUT or self.waiting_apothecary:
            return [ActionChoice(ActionType.USE_APOTHECARY, team=self.home),
                ActionChoice(ActionType.DONT_USE_APOTHECARY, team=self.home)]
        else:
            return [ActionChoice(ActionType.SELECT_ROLL, team=self.home, indexes=[0, 1])]


class Armor(Procedure):

    def __init__(self, game, home, player_id, modifiers=0, opp_player_id=None, foul=False):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.modifiers = modifiers
        self.opp_player_id = opp_player_id
        self.skip_armor = False
        self.armor_rolled = False
        self.player = game.get_player(player_id)
        self.foul = foul
        self.opp_player = None
        if self.opp_player_id is not None:
            self.opp_player = game.get_player(opp_player_id)

    def step(self, action):

        # Roll
        roll = DiceRoll([D6(), D6()])
        roll.modifiers = self.modifiers
        result = roll.get_sum() + self.modifiers
        self.armor_rolled = True

        armor_broken = False
        mighty_blow_used = False
        dirty_player_used = False

        if not self.foul:
            # Armor broken - Claws
            if result >= 8 and self.opp_player is not None and self.opp_player.has_skill(Skill.CLAWS):
                armor_broken = True

            # Armor broken
            if result > self.player.get_av():
                armor_broken = True

            # Armor broken - Might Blow
            if self.opp_player is not None and self.opp_player.has_skill(Skill.MIGHTY_BLOW) and result + 1 > self.player.get_av():
                roll.modifiers += 1
                armor_broken = True
                mighty_blow_used = True
        else:

            # Armor broken - Dirty player
            if self.opp_player is not None and self.opp_player.has_skill(Skill.DIRTY_PLAYER) and result + 1 > self.player.get_av():
                roll.modifiers += 1
                armor_broken = True
                dirty_player_used = True

            # Armor broken
            if result > self.player.get_av():
                armor_broken = True

        # Referee
        ejected = False
        if self.foul:
            if roll.same():
                if not (self.opp_player.has_skill(Skill.SNEAKY_GIT) and not armor_broken):
                    self.game.report(Outcome(OutcomeType.PLAYER_EJECTED, player_id=self.opp_player_id))
                    Turnover(self.game, self.home)
                    Ejection(self.game, self.home, self.player_id)
                    ejected = True

        # Break armor - roll injury
        if armor_broken:
            Injury(self.game, self.home, self.player_id, self.opp_player_id, foul=self.foul,
                   mighty_blow_used=mighty_blow_used, dirty_player_used=dirty_player_used, ejected=ejected)
            self.game.report(Outcome(OutcomeType.ARMOR_BROKEN, player_id=self.player_id,
                                     opp_player_id=self.opp_player_id, rolls=[roll]))
        else:
            self.game.report(Outcome(OutcomeType.ARMOR_NOT_BROKEN, player_id=self.player_id,
                                     opp_player_id=self.opp_player_id,  rolls=[roll]))

        return True

    def available_actions(self):
        return []


class Block(Procedure):

    def __init__(self, game, home, player_from, player_to, pos_to, blitz=False, frenzy=False, gfi=False):
        super().__init__(game)
        self.home = home
        self.player_from = player_from
        self.player_to = player_to
        self.pos_from = self.game.state.field.get_player_position(player_from.player_id)
        self.pos_to = pos_to
        self.reroll_used = False
        self.roll = None
        self.blitz = blitz
        self.gfi = gfi
        self.frenzy = frenzy
        self.waiting_wrestle_from = False
        self.waiting_wrestle_to = False
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
            GFI(self.game, self.home, self.player_from, self.pos_from, self.pos_to)
            return False

        # Frenzy check
        if self.frenzy and not self.frenzy_check:
            # Check if player was not pushed out of bounds
            if self.game.state.field.get_player_position(self.player_to.player_id) is None:
                return True
            self.game.report(Outcome(OutcomeType.FRENZY_USED, player_id=self.player_from.player_id,
                                     opp_player_id=self.player_to.player_id, team_home=self.home))
            self.frenzy_check = True

        # Roll
        if self.roll is None:

            # Determine dice and favor
            st_from = self.player_from.get_st()
            st_to = self.player_to.get_st()

            # Horns
            if self.blitz and self.player_from.has_skill(Skill.HORNS):
                st_from += 1

            # Dauntless
            if st_to > st_from and self.player_from.has_skill(Skill.DAUNTLESS) and self.dauntless_roll is None:
                self.dauntless_roll = DiceRoll([D6()])
                self.dauntless_success = self.dauntless_roll.get_sum() + st_from > st_to
                self.game.report(Outcome(OutcomeType.DAUNTLESS_USED, team_home=self.home, player_id=self.player_from.id, rolls=[self.dauntless_roll], n=True))
                return False
            elif self.dauntless_roll is not None and self.dauntless_success:
                st_from = st_to

            # Assists
            assists_from = self.game.state.field.assists(self.home, self.player_from, self.player_to)
            assists_to = self.game.state.field.assists(not self.home, self.player_to, self.player_from)
            st_from = st_from + assists_from
            st_to = st_to + assists_to

            # Determine dice and favor
            dice = 0
            if st_from * 2 < st_to:
                dice = 3
                self.favor = not self.home
            elif st_from < st_to:
                dice = 2
                self.favor = not self.home
            elif st_from == st_to:
                dice = 1
                self.favor = self.home
            elif st_from > st_to * 2:
                dice = 3
                self.favor = self.home
            elif st_from > st_to:
                dice = 2
                self.favor = self.home

            # Roll
            self.roll = DiceRoll([])
            for i in range(dice):
                self.roll.dice.append(BBDie())

            return False

        elif self.waiting_wrestle_to and action.team_home != self.home:

            self.wrestle = action.action_type == ActionType.USE_WRESTLE
            self.waiting_wrestle_to = False
            self.selected_die = BBDieResult.BOTH_DOWN

        else:

            # Re-roll
            if action.action_type == ActionType.USE_REROLL:

                # Roll again
                self.reroll_used = True
                self.game.state.get_team_state(self.home).use_reroll()
                return self.step(None)

            # Juggernaut - change 'both down' to 'push'
            if action.action_type == ActionType.USE_JUGGERNAUT:

                if not self.player_from.has_skill(Skill.JUGGERNAUT):
                    raise IllegalActionExcpetion("Player does not have the Juggernaut skill")

                if not self.blitz:
                    raise IllegalActionExcpetion("Juggernaut can only be used in blitz actions")

                if not self.roll.contains(BBDieResult.BOTH_DOWN):
                    raise IllegalActionExcpetion("Dice is not 'both down'")

                self.selected_die = BBDieResult.PUSH

            # Wrestle
            if action.action_type == ActionType.USE_WRESTLE:

                if not self.player_to.has_skill(Skill.WRESTLE):
                    raise IllegalActionExcpetion("Player does not have the Wrestle skill")

                if not self.roll.contains(BBDieResult.BOTH_DOWN):
                    raise IllegalActionExcpetion("Roll does not contain 'Both Down'")

                self.wrestle = True

            # Select dice
            if not self.wrestle:

                if action.action_type == ActionType.SELECT_DIE:

                    if (action.team_home != self.home and self.favor) or (action.team_home == self.home and not self.favor):
                        raise IllegalActionExcpetion("The other team has to select a die")

                    die = self.roll.dice[action.idx]

                    if die.get_value() == BBDieResult.ATTACKER_DOWN:
                        self.selected_die = BBDieResult.ATTACKER_DOWN

                    if die.get_value == BBDieResult.BOTH_DOWN:

                        # Wrestle - opponent
                        if self.player_to.has_skill(Skill.WRESTLE) and \
                                not (self.player_from.has_skill(Skill.JUGGERNAUT) and self.blitz):
                            self.waiting_wrestle_to = True

                    return True

        # Effect
        if self.wrestle:
            if self.game.state.field.has_ball(self.player_from.player_id):
                Turnover(self.game, self.home)
            KnockDown(self.game, self.home, self.player_from.player_id, opp_player_id=self.player_to.player_id, armor_roll=False, injury_roll=False, both_down=True)
            return True

        if self.selected_die == BBDieResult.ATTACKER_DOWN:
            Turnover(self.game, self.home)
            KnockDown(self.game, self.home, self.player_from.player_id, opp_player_id=self.player_to.player_id)
            return True

        if self.selected_die == BBDieResult.BOTH_DOWN:
            if not self.player_from.has_skill(Skill.BLOCK):
                Turnover(self.game, self.home)
                if not self.player_to.has_skill(Skill.BLOCK):
                    KnockDown(self.game, self.home, self.player_from.player_id, opp_player_id=self.player_to.player_id, both_down=True)
                else:
                    KnockDown(self.game, self.home, self.player_from.player_id, opp_player_id=self.player_to.player_id, both_down=False)
            elif not self.player_to.has_skill(Skill.BLOCK):
                KnockDown(self.game, self.home, self.player_to.player_id, opp_player_id=self.player_from.id)
            return True

        if self.selected_die == BBDieResult.DEFENDER_DOWN:
            Push(self.game, self.home, self.player_to, player_to=self.player_from, knock_down=True, blitz=self.blitz)
            return True

        if self.selected_die == BBDieResult.DEFENDER_STUMBLES:
            if not self.player_to.has_skill(Skill.DODGE):
                Push(self.game, self.home, self.player_to, player_to=self.player_from.id, knock_down=True, blitz=self.blitz)
            return True

        if self.selected_die == BBDieResult.PUSH:
            Push(self.game, self.home, self.player_to, player_to=self.player_from.id, knock_down=False, blitz=self.blitz)

            return True
        return False

    def available_actions(self):
        return []


class Bounce(Procedure):

    def __init__(self, game, home, kick=False):
        super().__init__(game)
        self.home = home  # With turn / kicking team
        self.kick = kick

    def step(self, action):

        # Roll
        roll_scatter = DiceRoll([D8()])
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

        self.game.state.field.ball_position.x += x
        self.game.state.field.ball_position.y += y

        self.game.report(Outcome(OutcomeType.BALL_SCATTER, pos=self.game.state.field.ball_position,
                                         team_home=self.home, rolls=[roll_scatter]))

        if self.kick:
            # Kick - out of bounds
            if self.game.state.field.is_ball_out() or \
                    not self.game.arena.is_team_side(self.game.state.field.ball_position, not self.home):
                Touchback(self.game, not self.home)
                self.game.report(Outcome(OutcomeType.TOUCHBACK, pos=self.game.state.field.ball_position,
                                         team_home=not self.home, rolls=[roll_scatter]))
                return True
        else:
            # Out of bounds
            if self.game.state.field.is_ball_out():
                ThrowIn(self.game, self.home, self.game.state.field.ball_position)
                self.game.report(Outcome(OutcomeType.BALL_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                         team_home=self.home, rolls=[roll_scatter]))
                return True

        # On player -> Catch
        player_id = self.game.state.field.get_player_id_at(self.game.state.field.ball_position)
        if player_id is not None:
            Catch(self.game, self.game.get_home_by_player_id(player_id), player_id, self.game.state.field.ball_position)
            self.game.report(Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.game.state.field.ball_position,
                                     player_id=player_id, rolls=[roll_scatter]))
            return True

        self.game.report(Outcome(OutcomeType.BALL_ON_GROUND, pos=self.game.state.field.ball_position, team_home=self.home))
        return True

    def available_actions(self):
        return []


class Casualty(Procedure):

    miss_next_game = [CasualtyEffect.MNG, CasualtyEffect.AG, CasualtyEffect.AV, CasualtyEffect.MA, CasualtyEffect.ST, CasualtyEffect.NI]

    def __init__(self, game, home, player_id, roll, opp_player_id=None):
        super().__init__(game)
        self.game = game
        self.home = home
        self.player_id = player_id
        self.opp_player_id = opp_player_id
        self.player = game.get_player(player_id)
        self.waiting_apothecary = False
        self.roll = roll
        self.casualty = None
        self.effect = None

    def step(self, action):

        self.roll = DiceRoll([D6(), D8()])
        result = self.roll.get_sum()
        n = min(61, max(38, result))
        self.casualty = CasualtyType(n)
        self.effect = Rules.casualty_effect[self.casualty]

        self.game.report(Outcome(OutcomeType.CASUALTY, player_id=self.player_id, team_home=self.home, n=self.effect.name, rolls=[self.roll]))

        if self.game.state.get_team_state(self.home).apothecary_available:
            Apothecary(self.game, self.home, self.player_id, roll=self.roll, outcome=OutcomeType.CASUALTY, casualty=self.casualty, effect=self.effect, opp_player_id=self.opp_player_id)
        else:
            # Apply casualty
            if self.effect == CasualtyEffect.NONE:
                self.game.state.casualty(self.player_id, self.home, PlayerState.BH, self.effect)
            elif self.effect in Casualty.miss_next_game:
                self.game.state.casualty(self.player_id, self.home, PlayerState.MNG, self.effect)
            elif self.effect == CasualtyEffect.DEAD:
                self.game.state.casualty(self.player_id, self.home, PlayerState.DEAD, self.effect)

        return True

    def available_actions(self):
        return []


class Catch(Procedure):

    #          0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    success = [6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1]

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
        self.game.state.field.move_ball(self.pos)
        self.interception = interception

    def step(self, action):

        # Otherwise roll if player hasn't rolled
        if not self.rolled:

            # Can player even catch ball?
            player = self.game.get_player(self.player_id)
            if player.has_skill(Skill.NO_HANDS) or self.game.state.get_player_state(self.player_id, self.home) not in Rules.ready_to_catch:
                Bounce(self.game, self.home)
                self.game.report(Outcome(OutcomeType.BALL_DROPPED, player_id=self.player_id))
                return True

            # Set modifiers
            modifiers = 1 if self.accurate else 0
            modifiers = -2 if self.interception else modifiers
            if self.interception and player.has_skill(Skill.LONG_LEGS):
                modifiers += 1

            pos = self.game.state.field.get_player_position(self.player_id)
            tackle_zones = self.game.state.field.get_tackle_zones(pos, home=self.home)
            modifiers -= tackle_zones

            # Weather
            if self.game.state.weather == WeatherType.POURING_RAIN:
                modifiers -= 1

            if player.has_skill(Skill.EXTRA_ARMS):
                modifiers += 1

            # Find success target
            target = Catch.success[player.get_ag()]

            # Roll
            roll = DiceRoll([D6()], target=target)
            roll.modifiers = modifiers
            result = roll.get_sum()
            mod_result = max(1, min(6, result + roll.modifiers))
            if result == 6 or (result != 1 and mod_result >= target):
                if self.interception:
                    self.game.report(Outcome(OutcomeType.INTERCEPTION, player_id=self.player_id), rolls=[roll])
                    Turnover(self.game, not self.home)
                else:
                    self.game.report(Outcome(OutcomeType.CATCH, player_id=self.player_id, rolls=[roll]))
                return True
            else:
                # Check if catch
                if player.has_skill(Skill.CATCH) and not self.catch_used:
                    self.catch_used = True
                    self.waiting_for_catch = True
                    self.game.report(Outcome(OutcomeType.CATCH_FAILED_CATCH, player_id=self.player_id, pos=self.pos, rolls=[roll]))
                    return False

                # Check if reroll available
                if self.game.state.can_use_reroll(self.home) and not self.catch_used:
                    self.waiting_for_reroll = True
                    self.game.report(Outcome(OutcomeType.CATCH_FAILED, player_id=self.player_id, rolls=[roll]))
                    return False

                Bounce(self.game, self.home)
                self.game.report(Outcome(OutcomeType.CATCH_FAILED, player_id=self.player_id, rolls=[roll]))
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
                self.game.state.use_reroll(self.home)
                self.rolled = False
                return self.step(None)
            else:
                Bounce(self.game, self.home)

        return True

    def available_actions(self):
        if self.waiting_for_reroll:
            return [ActionChoice(ActionType.USE_REROLL, team=self.home), ActionChoice(ActionType.DONT_USE_REROLL, team=self.home)]
        return []


class CoinToss(Procedure):

    def __init__(self, game):
        super().__init__(game)
        self.away_won_toss = None
        self.aa = [ActionChoice(ActionType.HEADS, team=False),
                   ActionChoice(ActionType.TAILS, team=False)]

    def step(self, action):
        if self.away_won_toss is None:
            self.flip_coin(action)
            return False
        elif self.away_won_toss is not None:
            self.pick(action)
            return True

    def flip_coin(self, action):
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

    def pick(self, action):
        if action.action_type == ActionType.KICK:
            self.game.state.kicking_team = not self.away_won_toss
        elif action.action_type == ActionType.RECEIVE:
            self.game.state.kicking_team = self.away_won_toss
        if self.game.state.kicking_team:
            self.game.report(Outcome(OutcomeType.AWAY_RECEIVE, team_home=False))
        else:
            self.game.report(Outcome(OutcomeType.HOME_RECEIVE))

    def available_actions(self):
        return self.aa


class DeterminePassSuccess(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.game = game
        self.home = home

    def step(self, action):

        ball_at = self.game.state.field.ball_position
        player_at = self.game.state.field.get_player_id_at(ball_at)
        if player_at is None or self.game.get_home_by_player_id(player_at) != self.home:
            Turnover(self.game, self.home)

        return True

    def available_actions(self):
        return []


class Ejection(Procedure):

    def __init__(self, game, home, player_id):
        super().__init__(game)
        self.home = home  # With turn
        self.player_id = player_id

    def step(self, action):

        self.game.state.field.remove(self.player_id)
        self.game.state.get_dugout(self.home).dungeon.append(self.player_id)
        self.game.state.set_player_state(self.player_id, self.home, PlayerState.EJECTED)

        return True

    def available_actions(self):
        return []


class Foul(Procedure):

    def __init__(self, game, home, player_from, player_to):
        super().__init__(game)
        self.home = home
        self.player_from = player_from
        self.player_to = player_to
        self.pos_from = self.game.state.field.get_player_position(player_from.player_id)
        self.pos_to = self.game.state.field.get_player_position(self.player_to)

    def step(self, action):

        # Assists
        assists_from = self.game.state.field.assists(self.home, self.player_from, self.player_to, ignore_guard=True)
        assists_to = self.game.state.field.assists(not self.home, self.player_to, self.player_from, ignore_guard=True)
        modifier = assists_from - assists_to

        self.game.report(Outcome(OutcomeType.FOUL, player_id=self.player_from.player_id, opp_player_id=self.player_to.player_id))

        # Armor roll
        Armor(self.game, self.home, self.player_to.player_id, modifiers=modifier, opp_player_id=self.player_from.player_id, foul=True)

        return True

    def available_actions(self):
        return []


class ResetHalf(Procedure):

    def __init__(self, game):
        super().__init__(game)

    def step(self, action):
        self.game.state.home_state.rerolls = self.game.home.rerolls
        self.game.state.away_state.rerolls = self.game.away.rerolls
        return True

    def available_actions(self):
        return []


class Half(Procedure):

    def __init__(self, game, half):
        super().__init__(game)
        self.half = half

        # Determine kicking team
        self.kicking_team = self.game.state.kicking_team if self.half == 1 \
            else not self.game.state.kicking_team

        # Add turns
        for i in range(8):
            Turn(self.game, self.kicking_team, self.half, 8-i)
            Turn(self.game, not self.kicking_team, self.half, 8-i)

        # Setup and kickoff
        KickOff(self.game, self.kicking_team)
        Setup(self.game, home=not self.kicking_team)
        Setup(self.game, home=self.kicking_team)
        ResetHalf(self.game)
        ClearBoard(self.game)

        # If second half
        if self.half > 1:
            PreHalf(self.game, False)
            PreHalf(self.game, True)

    def step(self, action):
        if self.half == 1:
            self.game.report(Outcome(OutcomeType.END_OF_FIRST_HALF))
        elif self.half == 2:
            self.game.report(Outcome(OutcomeType.END_OF_SECOND_HALF))
        return True

    def available_actions(self):
        return []


class Injury(Procedure):

    def __init__(self, game, home, player_id, opp_player_id=None, foul=False, mighty_blow_used=False, dirty_player_used=False,
                 ejected=False):
        super().__init__(game)
        self.game = game
        self.home = home
        self.player_id = player_id
        self.opp_player_id = opp_player_id
        self.injury_rolled = False
        self.foul = foul
        self.mighty_blow_used = mighty_blow_used
        self.dirty_player_used = dirty_player_used
        self.ejected = ejected
        self.player = game.get_player(player_id)
        self.opp_player = game.get_player(opp_player_id) if opp_player_id is not None else None
        self.apothecary_used = False

    def step(self, action):

        # TODO: Necromancer

        # Roll
        roll = DiceRoll([D6(), D6()])
        result = roll.get_sum()
        self.injury_rolled = True

        # Skill modifiers
        thick_skull = -1 if self.player.has_skill(Skill.THICK_SKULL) else 0
        stunty = 1 if self.player.has_skill(Skill.STUNTY) else 0
        mighty_blow = 0
        dirty_player = 0
        if self.opp_player is not None:
            mighty_blow = 1 if self.opp_player.has_skill(Skill.MIGHTY_BLOW) and not self.mighty_blow_used and not self.foul else 0
            dirty_player = 1 if self.opp_player.has_skill(Skill.DIRTY_PLAYER) and not self.dirty_player_used and self.foul else 0

        # STUNNED
        if result + thick_skull + stunty + mighty_blow + dirty_player <= 7:
            roll.modifiers = thick_skull + stunty + mighty_blow + dirty_player
            if self.game.get_player(self.player_id).has_skill(Skill.BALL_AND_CHAIN):
                KnockOut(self.game, self.home, self.player_id, roll=roll, opp_player_id=self.opp_player_id)
            else:
                self.game.state.get_team_state(self.home).player_states[self.player_id] = PlayerState.STUNNED
                self.game.report(Outcome(OutcomeType.STUNNED, player_id=self.player_id, opp_player_id=self.opp_player_id, rolls=[roll]))

        # CASUALTY
        elif result + stunty + mighty_blow + dirty_player >= 10:
            roll.modifiers = stunty + mighty_blow + dirty_player
            self.game.report(Outcome(OutcomeType.CASUALTY, player_id=self.player_id, opp_player_id=self.opp_player_id, rolls=[roll]))
            Casualty(self.game, self.home, self.player_id, roll, opp_player_id=self.opp_player_id)

        # KOD
        else:
            roll.modifiers = thick_skull + stunty + mighty_blow + dirty_player
            KnockOut(self.game, self.home, self.player_id, roll=roll, opp_player_id=self.opp_player_id)

        # Referee
        if self.foul and not self.ejected:
            if roll.same():
                if not self.opp_player.has_skill(Skill.SNEAKY_GIT):
                    self.game.report(Outcome(OutcomeType.PLAYER_EJECTED, player_id=self.opp_player_id))
                    Turnover(self.game, self.home)
                    Ejection(self.game, self.home, self.player_id)

        return True

    def available_actions(self):
        return []


class Interception(Procedure):

    def __init__(self, game, home, interceptors):
        super().__init__(game)
        self.home = home
        self.interceptors = interceptors

    def step(self, action):

        if action.action_type == ActionType.INTERCEPTION:

            if action.player_from_id not in self.interceptors:
                raise IllegalActionExcpetion("The selected player cannot intercept")

            pos = self.game.state.field.get_player_position(action.player_from_id)
            Catch(self.game, self.home, action.player_from_id, pos, interception=True)

        return True

    def available_actions(self):
        return []


class Touchback(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.home = home  # Player who can place the ball

    def step(self, action):
        pos = self.game.state.field.get_player_position(action.player_from_id)
        self.game.state.field.move_ball(pos)
        self.game.report(Outcome(OutcomeType.TOUCHBACK_BALL_PLACED, player_id=action.player_from_id, pos=pos))
        return True

    def available_actions(self):
        return [ActionChoice(ActionType.SELECT_PLAYER, team=self.home, player_ids=self.game.state.field.get_team_player_ids(self.home))]


class LandKick(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.home = home  # Kicking team
        self.landed = False

    def step(self, action):

        # Gentle gust
        if self.game.state.gentle_gust:
            Scatter(self.game, home=self.home, kick=True, gentle_gust=True)
            self.game.state.gentle_gust = False
            return False

        if not self.game.arena.is_team_side(self.game.state.field.ball_position, not self.home):
            Touchback(self.game, home=not self.home)
            self.game.report(Outcome(OutcomeType.TOUCHBACK, team_home=not self.home))
        else:
            self.game.state.field.ball_in_air = False
            player_id = self.game.state.field.get_player_id_at(self.game.state.field.ball_position)
            if player_id is None:
                Bounce(self.game, home=self.home, kick=True)
                self.game.report(Outcome(OutcomeType.BALL_HIT_GROUND, pos=self.game.state.field.ball_position,
                                         team_home=self.home))
            else:
                Catch(self.game, not self.home, player_id=player_id, pos=self.game.state.field.ball_position)
                self.game.report(Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.game.state.field.ball_position,
                                         team_home=not self.home, player_id=player_id))
        return True

    def available_actions(self):
        return []


class Fans(Procedure):

    def __init__(self, game):
        super().__init__(game)

    def step(self, action):
        roll_home = DiceRoll([D6(), D6()])
        roll_away = DiceRoll([D6(), D6()])
        fans_home = (roll_home.get_sum() + self.game.home.fan_factor) * 1000
        fans_away = (roll_away.get_sum() + self.game.away.fan_factor) * 1000
        self.game.state.spectators = fans_home + fans_away
        fame_team = None
        fame = 0
        if fans_home >= fans_away * 2:
            self.game.state.home_state.fame = 2
            fame = 2
            fame_team = True
        elif fans_home > fans_away:
            self.game.state.home_state.fame = 1
            fame_team = True
            fame = 1
        elif fans_away >= fans_home * 2:
            self.game.state.away_state.fame = 2
            fame_team = False
            fame = 2
        elif fans_away > fans_home:
            self.game.state.away_state.fame = 1
            fame = 1
            fame_team = False
        self.game.report(Outcome(OutcomeType.SPECTATORS, n=self.game.state.spectators, rolls=[roll_home, roll_away]))
        if fame == 0:
            self.game.report(Outcome(OutcomeType.NO_FAME, n=fame))
        else:
            self.game.report(Outcome(OutcomeType.FAME, n=fame, team_home=fame_team))

        return True

    def available_actions(self):
        return []


class KickOff(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.kicking_home = home
        self.game.state.gentle_gust = False
        self.game.state.reset_kickoff()
        LandKick(game, home=self.kicking_home)
        KickOffTable(game, home=self.kicking_home)
        Scatter(game, home=self.kicking_home, kick=True)
        PlaceBall(game, home=self.kicking_home)

    def step(self, action):
        return True

    def available_actions(self):
        return []


class GetTheRef(Procedure):
    """
    Each team receives 1 additional Bribe to use during this game.
    """
    def __init__(self, game, home):
        super().__init__(game)
        self.home = home  # Receiving team

    def step(self, action):
        self.game.state.home_state.bribes += 1
        self.game.state.away_state.bribes += 1
        self.game.report(Outcome(OutcomeType.GET_THE_REF))
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
    def __init__(self, game, home):
        super().__init__(game)
        self.home = home  # Kicking team
        self.effect = 0

    def step(self, action):
        roll = None
        if self.game.state.get_team_state(not self.home).turn == 7:
            self.effect = -1
        elif self.game.state.get_team_state(not self.home).turn == 0:
            self.effect = 1
        else:
            roll = DiceRoll([D6()])
            if roll.get_sum() <= 3:
                self.effect = 1
            else:
                self.effect = -11

        self.game.state.get_team_state(self.home).turn += self.effect
        self.game.state.get_team_state(not self.home).turn += self.effect
        self.game.report(Outcome(OutcomeType.RIOT, n=self.effect, rolls=[] if roll is None else [roll]))
        return True

    def available_actions(self):
        return []


class HighKick\
            (Procedure):
    """
    High Kick: The ball is kicked very high, allowing a player on the receiving team time to move into the
    perfect position to catch it. Any one player on the receiving team who is not in an opposing player's
    tackle zone may be moved into the square where the ball will land no matter what their MA may be, as long
    as the square is unoccupied.
    """
    def __init__(self, game, home):
        super().__init__(game)
        self.home = home  # Receiving team

    def step(self, action):
        if action.action_type == ActionType.PLACE_PLAYER:
            self.game.state.field.move(action.player_from_id, action.pos_to)
            self.game.report(Outcome(OutcomeType.PLAYER_PLACED_HIGH_KICK, pos=action.pos_to, team_home=self.home))
        elif action.action_type == ActionType.END_SETUP:
            self.game.report(Outcome(OutcomeType.SETUP_DONE, team_home=self.home))
        return True

    def available_actions(self):
        if self.game.arena.is_team_side(self.game.state.field.ball_position, self.home) and self.game.state.field.get_player_id_at(self.game.state.field.ball_position) == None:
            return [ActionChoice(ActionType.PLACE_PLAYER, team=self.home, player_ids=self.game.state.field.get_team_player_ids(self.home), positions=[self.game.state.field.ball_position]),
                    ActionChoice(ActionType.SELECT_NONE, team=self.home)]
        else:
            return [ActionChoice(ActionType.SELECT_NONE, team=self.home)]


class CheeringFans(Procedure):
    """
    Each coach rolls a D3 and adds their team's FAME (see page 18) and the number of cheerleaders on their team to the
    score. The team with the highest score is inspired by their fans' cheering and gets an extra re-roll this half.
    If both teams have the same score, then both teams get a re-roll.
    """
    def __init__(self, game):
        super().__init__(game)

    def step(self, action):
        roll_home = DiceRoll([D3()])
        roll_away = DiceRoll([D3()])

        roll_home.modifiers = self.game.state.home_state.fame + self.game.state.home_state.cheerleaders
        roll_away.modifiers = self.game.state.away_state.fame + self.game.state.away_state.cheerleaders

        rh = roll_home.get_sum() + roll_home.modifiers
        ra = roll_away.get_sum() + roll_away.modifiers

        if rh >= ra:
            self.game.state.home_state.rerolls += 1
            self.game.report(Outcome(OutcomeType.CHEERING_FANS, team_home=True, rolls=[roll_home, roll_away]))
        if ra >= rh:
            self.game.state.away_state.rerolls += 1
            self.game.report(Outcome(OutcomeType.CHEERING_FANS, team_home=False, rolls=[roll_home, roll_away]))

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
        roll_home = DiceRoll([D3()])
        roll_away = DiceRoll([D3()])

        roll_home.modifiers = self.game.state.home_state.fame + self.game.state.home_state.ass_coaches
        roll_away.modifiers = self.game.state.away_state.fame + self.game.state.away_state.ass_coaches

        rh = roll_home.get_sum() + roll_home.modifiers
        ra = roll_away.get_sum() + roll_away.modifiers

        if rh >= ra:
            self.game.state.home_state.rerolls += 1
            self.game.report(Outcome(OutcomeType.BRILLIANT_COACHING, team_home=True, rolls=[roll_home, roll_away]))
        if ra >= rh:
            self.game.state.away_state.rerolls += 1
            self.game.report(Outcome(OutcomeType.BRILLIANT_COACHING, team_home=False, rolls=[roll_home, roll_away]))

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
        roll_home = DiceRoll([D6()])
        roll_away = DiceRoll([D6()])
        rh = roll_home.get_sum() + self.game.state.home_state.fame
        ra = roll_away.get_sum() + self.game.state.away_state.fame

        rh = 1
        ra = 1

        if ra >= rh:
            player_home_id = self.game.state.field.get_random_player(True)
            KnockDown(self.game, True, player_home_id, armor_roll=False)
            self.game.report(Outcome(OutcomeType.HIT_BY_ROCK, player_id=player_home_id, rolls=[roll_home, roll_away]))

        if rh >= ra:
            player_away_id = self.game.state.field.get_random_player(False)
            KnockDown(self.game, False, player_away_id, armor_roll=False)
            self.game.report(Outcome(OutcomeType.HIT_BY_ROCK, player_id=player_away_id, rolls=[roll_home, roll_away]))

        return True

    def available_actions(self):
        return []


class PitchInvasionRoll(Procedure):
    """
    ... If a roll is 6 or more after modification then the player is Stunned (players with the Ball & Chain skill are
    KO'd). A roll of 1 before adding FAME will always have no effect.
    """
    def __init__(self, game, home, player_id):
        super().__init__(game)
        self.home = home
        self.player_id = player_id

    def step(self, action):
        roll = DiceRoll([D6()])

        roll.modifiers = self.game.state.get_team_state(self.home).fame
        result = roll.get_sum() + roll.modifiers

        if result >= 6:
            if self.game.get_player(self.player_id).has_skill(Skill.BALL_AND_CHAIN):
                self.game.report(Outcome(OutcomeType.PITCH_INVASION_ROLL, rolls=[roll], player_id=self.player_id, team_home=self.home))
                KnockOut(self.game, self.home, self.player_id)
            else:
                self.game.state.set_player_state(self.player_id, self.home, PlayerState.STUNNED)
                self.game.report(Outcome(OutcomeType.PITCH_INVASION_ROLL, rolls=[roll], player_id=self.player_id, team_home=self.home, n=PlayerState.STUNNED.name))
        else:
            self.game.report(Outcome(OutcomeType.PITCH_INVASION_ROLL, rolls=[roll], player_id=self.player_id, team_home=self.home, n=PlayerState.READY.name))

        return True

    def available_actions(self):
        return []


class KickOffTable(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.home = home
        self.rolled = False

    def step(self, action):

        roll = DiceRoll([D6(), D6()])
        roll.result = roll.get_sum()

        self.rolled = True
        #roll.result = 5

        if roll.result == 2:  # Get the ref!
            GetTheRef(self.game, self.home)
            self.game.report(Outcome(OutcomeType.KICKOFF_GET_THE_REF, rolls=[roll]))
        elif roll.result == 3:  # Riot!
            Riot(self.game, self.home)
            self.game.report(Outcome(OutcomeType.KICKOFF_RIOT, rolls=[roll]))
        elif roll.result == 4:  # Perfect defense
            Setup(self.game, home=self.home, reorganize=True)
            self.game.report(Outcome(OutcomeType.KICKOFF_PERFECT_DEFENSE, team_home=self.home, rolls=[roll]))
        elif roll.result == 5:  # High Kick
            HighKick(self.game, home=not self.home)
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
            Turn(self.game, not self.home, None, None, quick_snap=True)
            self.game.report(Outcome(OutcomeType.KICKOFF_QUICK_SNAP, rolls=[roll]))
        elif roll.result == 10:  # Blitz
            Turn(self.game, self.home, None, None, blitz=True)
            self.game.report(Outcome(OutcomeType.KICKOFF_BLITZ, rolls=[roll]))
        elif roll.result == 11:  # Throw a Rock
            ThrowARock(self.game)
            self.game.report(Outcome(OutcomeType.KICKOFF_THROW_A_ROCK, rolls=[roll]))
        elif roll.result == 12:  # Pitch Invasion
            for player_id in self.game.state.field.get_team_player_ids(True):
                PitchInvasionRoll(self.game, True, player_id)
            for player_id in self.game.state.field.get_team_player_ids(False):
                PitchInvasionRoll(self.game, False, player_id)
            self.game.report(Outcome(OutcomeType.KICKOFF_PITCH_INVASION, rolls=[roll]))

        return True

    def available_actions(self):
        return []


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
        self.game.state.get_team_state(self.home).player_states[self.player_id] = PlayerState.DOWN_USED
        self.game.report(Outcome(OutcomeType.KNOCKED_DOWN, player_id=self.player_id, opp_player_id=self.opp_player_id))
        if self.both_down:
            self.game.state.get_team_state(not self.home).player_states[self.opp_player_id] = PlayerState.DOWN_USED
            self.game.report(Outcome(OutcomeType.KNOCKED_DOWN, player_id=self.opp_player_id, opp_player_id=self.player_id))

        # Turnover
        if self.turnover:
            Turnover(self.game, self.home)

        # Check fumble
        pos = self.game.state.field.get_player_position(self.player_id)
        if self.game.state.field.is_ball_at(pos):
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
            Armor(self.game, self.home, self.player_id, modifiers=self.modifiers, opp_player_id=self.opp_player_id)

        if self.both_down:
            if self.injury_roll and not self.armor_roll:
                Injury(self.game, not self.home, self.opp_player_id, opp_player_id=self.player_id if not self.in_crowd else None)
            elif self.armor_roll:
                Armor(self.game, not self.home, self.opp_player_id, modifiers=self.modifiers, opp_player_id=self.player_id)

        return True

    def available_actions(self):
        return []


class KnockOut(Procedure):

    def __init__(self, game, home, player_id, roll, opp_player_id=None):
        super().__init__(game)
        self.game = game
        self.home = home
        self.player_id = player_id
        self.opp_player_id = opp_player_id
        self.player = game.get_player(player_id)
        self.opp_player = game.get_player(opp_player_id) if opp_player_id is not None else None
        self.roll = roll

    def step(self, action):
        if self.game.state.get_team_state(self.home).apothecary_available:
            Apothecary(self.game, self.home, self.player_id, roll=self.roll, outcome=OutcomeType.KNOCKED_OUT, opp_player_id=self.opp_player_id)
            return True
        else:
            # Knock out player
            self.game.state.get_team_state(self.home).player_states[self.player_id] = PlayerState.KOD
            self.game.state.field.remove(self.player_id)
            self.game.state.get_dugout(self.home).kod.append(self.player_id)
            self.game.report(Outcome(OutcomeType.KNOCKED_OUT, rolls=[self.roll], player_id=self.player_id, team_home=self.home))

        return True

    def available_actions(self):
        return []


class Move(Procedure):

    def __init__(self, game, home, player_id, from_pos, to_pos, gfi, dodge):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.from_pos = from_pos
        self.to_pos = to_pos
        if gfi:
            GFI(game, home, player_id, from_pos, to_pos)
        if dodge:
            Dodge(game, home, player_id, from_pos, to_pos)

    def step(self, action):

        # TODO: Check if in bounds

        on_ball_before = self.game.state.field.has_ball(self.player_id)
        self.game.state.field.move(self.player_id, self.to_pos)
        on_ball_after = self.game.state.field.has_ball(self.player_id)

        # Check if player moved onto the ball
        if on_ball_before != on_ball_after:

            # Attempt to pick up the ball - unless no hands
            player = self.game.get_player(self.player_id)
            if player.has_skill(Skill.NO_HANDS):
                Bounce(self.game, self.home)
                return True
            else:
                Pickup(self.game, self.home, self.player_id, self.to_pos, cause_turnover=True)
                return True

        elif on_ball_before and self.game.arena.is_touchdown(self.to_pos, self.home):

            # Touchdown if player had the ball with him/her
            Touchdown(self.game, self.home, self.player_id)

        return True

    def available_actions(self):
        return []


class GFI(Procedure):

    def __init__(self, game, home, player_id, from_pos, to_pos):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.awaiting_reroll = False
        self.awaiting_sure_feet = False
        self.sure_feet_used = False
        self.reroll_used = False
        self.rolled = False

    def step(self, action):

        # If player hasn't rolled
        if not self.rolled:

            # Roll
            roll = DiceRoll([D6()])
            self.rolled = True
            roll.modifiers = 1 if self.game.state.weather == WeatherType.BLIZZARD else 0

            if roll.get_sum() >= 2 + roll.modifiers:

                # Success
                self.game.report(Outcome(OutcomeType.SUCCESSFUL_GFI, player_id=self.player_id, pos=self.to_pos, rolls=[roll]))
                return True

            else:

                # Fail
                self.game.report(Outcome(OutcomeType.FAILED_GFI, player_id=self.player_id, pos=self.to_pos, rolls=[roll]))

                # Check if sure feet
                player = self.game.get_player(self.player_id)
                if player.has_skill(Skill.SURE_FEET) and not self.sure_feet_used:
                    self.sure_feet_used = True
                    self.awaiting_sure_feet = True
                    return False

                # Check if reroll available
                if self.game.state.can_use_reroll(self.home) and not self.sure_feet_used:
                    self.awaiting_reroll = True
                    self.game.report(Outcome(OutcomeType.FAILED_GFI, player_id=self.player_id, pos=self.to_pos, rolls=[roll]))
                    return False

                # Player trips
                self.game.state.field.move(self.player_id, self.to_pos)
                KnockDown(self.game, self.home, self.player_id, self.to_pos, turnover=True)
                return True

        # If sure feet used
        if self.awaiting_sure_feet:
            if action.action_type == ActionType.USE_SKILL:
                self.sure_feet_used = True
                self.rolled = False
                self.step(None)
            else:
                # Player trips
                self.game.state.field.move(self.player_id, self.to_pos)
                KnockDown(self.game, self.home, self.player_id, self.to_pos, turnover=True)
                return True

        # If reroll used
        if self.awaiting_reroll:
            if action.action_type == ActionType.USE_REROLL:
                # Remove reroll and roll again - recursive call
                self.game.state.get_team_state(self.home).reroll_used = True
                self.game.state.get_team_state(self.home).rerolls -= 1
                self.rolled = False
                self.step(None)
            else:
                # Player trips
                self.game.state.field.move(self.player_id, self.to_pos)
                KnockDown(self.game, self.home, self.player_id, self.to_pos, turnover=True)
                return True

    def available_actions(self):
        return []


class EndPlayerTurn(Procedure):

    def __init__(self, game, home, player_id):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.player = self.game.get_player(player_id)

    def step(self, action):
        return True

    def available_actions(self):
        return []


class Dodge(Procedure):

    #          0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    success = [6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1]

    def __init__(self, game, home, player_id, from_pos, to_pos, cause_turnover=True):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.player = self.game.get_player(player_id)
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.dodge_used = False
        self.awaiting_dodge = False
        self.awaiting_reroll = False
        self.rolled = False
        self.cause_turnover = cause_turnover

    def step(self, action):

        # If player hasn't rolled
        if not self.rolled:

            # Check opp skills
            tackle_zones_from, tackle_ids_from, prehensile_tail_ids_from, diving_tackle_ids_from, shadowing_ids_from, tentacles_ids_from = self.game.state.field.get_tackle_zones_detailed(self.from_pos)

            tackle_zones_to = self.game.state.field.get_tackle_zones(self.to_pos, home=self.home)

            # TODO: Allow player to select if shadowing and diving tackle
            # TODO: Put diving tackle or shadowing proc on stack
            # TODO: Auto-use other skills

            # Roll
            roll = DiceRoll([D6()])
            self.rolled = True

            # Calculate target
            roll.modifiers = 1
            ignore_opp_mods = False
            if self.player.has_skill(Skill.STUNTY):
                roll.modifiers = 1
                ignore_opp_mods = True
            if self.player.has_skill(Skill.TITCHY):
                roll.modifiers -= 1
                ignore_opp_mods = True
            if self.player.has_skill(Skill.TWO_HEADS):
                roll.modifiers -= 1

            if not ignore_opp_mods:
                roll.modifiers -= tackle_zones_to

            # Break tackle - use st instead of ag
            attribute = self.player.get_ag()
            if self.player.has_skill(Skill.BREAK_TACKLE) and self.player.get_st() > self.player.get_st():
                attribute = self.player.get_st()

            roll.target = Dodge.success[attribute]

            if roll.is_d6_success():

                # Success
                self.game.report(Outcome(OutcomeType.SUCCESSFUL_DODGE, player_id=self.player_id, pos=self.to_pos, rolls=[roll]))
                return True

            else:

                # Fail
                self.game.report(Outcome(OutcomeType.FAILED_DODGE, player_id=self.player_id, pos=self.to_pos, rolls=[roll]))

                # Check if sure feet
                if self.player.has_skill(Skill.DODGE) and not self.dodge_used:
                    self.dodge_used = True
                    self.awaiting_dodge = True
                    return False

                # Check if reroll available
                if self.game.state.can_use_reroll(self.home) and not self.dodge_used:
                    self.awaiting_reroll = True
                    return False

                # Player trips
                self.game.state.field.move(self.player_id, self.to_pos)
                KnockDown(self.game, self.home, self.player_id, turnover=self.cause_turnover)

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
                self.game.state.use_reroll(self.home)
                self.rolled = False
                return self.step(None)
            else:
                # Player trips
                self.game.state.field.move(self.player_id, self.to_pos)
                KnockDown(self.game, self.home, self.player_id, turnover=self.cause_turnover)
                return True

    def available_actions(self):
        if self.awaiting_reroll:
            return [ActionChoice(ActionType.USE_REROLL, team=self.home), ActionChoice(ActionType.DONT_USE_REROLL, team=self.home)]
        return []


class PassAction(Procedure):

    #          0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    success = [6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1]

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

    def available_actions(self):
        return []


class Pickup(Procedure):

    #          0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    success = [6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1]

    def __init__(self, game, home, player_id, pos, cause_turnover=True):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.pos = pos
        self.rolled = False
        self.sure_hands_used = False
        self.waiting_for_reroll = False
        self.waiting_for_sure_hands = False
        self.cause_turnover = cause_turnover

    def step(self, action):

        # Otherwise roll if player hasn't rolled
        if not self.rolled:

            player = self.game.get_player(self.player_id)
            pos = self.game.state.field.get_player_position(player.player_id)
            tackle_zones = self.game.state.field.get_tackle_zones(pos, home=self.home)

            roll = DiceRoll([D6()])
            roll.target = Pickup.success[player.get_ag()]
            roll.modifiers = 1

            if not player.has_skill(Skill.BIG_HAND):
                roll.modifiers -= tackle_zones

            # Weather
            if self.game.state.weather == WeatherType.POURING_RAIN:
                if not player.has_skill(Skill.BIG_HAND):
                    roll.modifiers -= 1

            # Extra arms
            if player.has_skill(Skill.EXTRA_ARMS):
                roll.modifiers += 1

            # Can player even handle the ball?
            if player.has_skill(Skill.NO_HANDS):
                Bounce(self.game, self.home)
                self.game.report(Outcome(OutcomeType.FAILED_PICKUP, player_id=self.player_id))
                return True

            # Roll
            self.rolled = True
            if roll.is_d6_success():
                self.game.report(Outcome(OutcomeType.SUCCESSFUL_PICKUP, player_id=self.player_id, rolls=[roll]))
                return True
            else:
                # Check if sure hands
                if player.has_skill(Skill.SURE_HANDS) and not self.sure_hands_used:
                    self.sure_hands_used = True
                    self.waiting_for_sure_hands = True
                    self.game.report(Outcome(OutcomeType.FAILED_PICKUP, player_id=self.player_id, pos=self.pos, rolls=[roll]))
                    return False

                # Check if reroll available
                if self.game.state.can_use_reroll(self.home) and not self.sure_hands_used:
                    self.waiting_for_reroll = True
                    self.game.report(Outcome(OutcomeType.FAILED_PICKUP, player_id=self.player_id, rolls=[roll]))
                    return False

                # Turnover?
                if self.cause_turnover:
                    Turnover(self.game, self.home)

                Bounce(self.game, self.home)
                self.game.report(Outcome(OutcomeType.FAILED_PICKUP, player_id=self.player_id, rolls=[roll]))

                return True

        # If has sure hands
        if self.waiting_for_sure_hands:
            self.sure_hands_used = True
            self.rolled = False
            return self.step(None)

        # If re-roll used
        if self.waiting_for_reroll:
            if action.action_type == ActionType.USE_REROLL:
                self.game.state.use_reroll(self.home)
                self.rolled = False
                return self.step(None)
            else:
                Bounce(self.game, self.home)
                # Turnover?
                if self.cause_turnover:
                    Turnover(self.game, self.home)

        return True

    def available_actions(self):
        if self.waiting_for_reroll:
            return [ActionChoice(ActionType.USE_REROLL, team=self.home), ActionChoice(ActionType.DONT_USE_REROLL, team=self.home)]
        return []


class StandUp(Procedure):

    def __init__(self, game, home, player_id, roll=False):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.roll = roll

    def step(self, action):

        if self.roll:
            roll = DiceRoll([D6()], target=4)
            if roll.is_d6_success:
                self.game.state.set_player_state(self.player_id, self.home, PlayerState.READY)
                self.game.report(Outcome(OutcomeType.PLAYER_STAND_UP_SUCCESS, rolls=[roll], player_id=self.player_id))
            else:
                self.game.state.set_player_state(self.player_id, self.home, PlayerState.DOWN_USED)
                self.game.report(Outcome(OutcomeType.PLAYER_STAND_UP_FAILUE, rolls=[roll], player_id=self.player_id))
        else:
            self.game.state.set_player_state(self.player_id, self.home, PlayerState.READY)

        return True

    def available_actions(self):
        return []


class PlaceBall(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.home = home
        self.aa = [ActionChoice(ActionType.PLACE_BALL, team=self.home, positions=self.game.arena.get_team_side(not self.home))]

    def step(self, action):
        if not self.game.arena.is_team_side(action.pos_to, self.home):
            self.game.state.field.move_ball(action.pos_to, in_air=True)
            self.game.report(Outcome(OutcomeType.BALL_PLACED, pos=action.pos_to, team_home=self.home))
        else:
            raise IllegalActionExcpetion("Illegal position")
        return True

    def available_actions(self):
        return self.aa


class PlayerAction(Procedure):

    def __init__(self, game, home, player_id, player_action_type, turn):
        super().__init__(game)
        self.home = home
        self.player_id = player_id
        self.player_from = self.game.get_player(player_id)
        self.player_action_type = player_action_type
        self.moves = 0
        self.turn = turn

    def step(self, action):

        if action.action_type == ActionType.END_PLAYER_TURN:
            self.game.state.set_player_state(self.player_id, self.home, PlayerState.USED)
            self.game.report(Outcome(OutcomeType.END_PLAYER_TURN))
            return True

        # Action attributes
        player_to = self.game.get_player(action.player_to_id) if action.player_to_id is not None else None

        player_state_from = self.game.state.get_player_state(self.player_id, self.home)
        player_state_to = self.game.state.get_player_state(action.player_to_id, self.home) if player_to is not None else None

        if action.action_type == ActionType.STAND_UP:

            StandUp(self.game, self.home, self.player_id, roll=self.player_from.get_ma() < 3)
            self.moves += 3

        elif action.action_type == ActionType.MOVE:

            # Check GFI
            gfi = self.moves + 1 > self.player_from.get_ma()

            # Check dodge
            dodge = False
            if not self.turn.quick_snap:
                if self.game.get_player(self.player_id).has_skill(Skill.BALL_AND_CHAIN):
                    # Ball and chain -> Auto-dodge
                    dodge = True
                    gfi = False
                else:
                    tackle_zones_from = self.game.state.field.get_tackle_zones(action.pos_from, home=self.home)
                    dodge = tackle_zones_from > 0

            # Add proc
            Move(self.game, self.home, self.player_id, action.pos_from, action.pos_to, gfi, dodge)
            self.moves += 1

            return False

        elif action.action_type == ActionType.BLOCK:

            # Check GFI
            gfi = False
            if action.action_type == ActionType.BLITZ:
                move_needed = 1 if player_state_from == PlayerState.DOWN_READY else 1
                gfi_allowed = 3 if self.player_from.has_skill(Skill.SPRINT) else 2
                if self.moves + move_needed > self.player_from.get_ma() + gfi_allowed:
                    raise IllegalActionExcpetion("No movement points left")
                gfi = self.moves + move_needed > self.player_from.get_ma()
                # Use movement
                self.moves += move_needed
                self.game.state.set_player_state(self.player_from.player_id, self.home, PlayerState.READY)

            # Check frenzy
            if self.player_from.has_skill(Skill.FRENZY):
                move_needed = 0
                if self.player_action_type == ActionType.BLITZ:
                    move_needed = 1
                gfi_allowed = 3 if self.player_from.has_skill(Skill.SPRINT) else 2
                if self.moves + move_needed <= self.player_from.get_ma() + gfi_allowed:
                    gfi_2 = self.moves + move_needed > self.player_from.get_ma()
                    Block(self.game, self.home, self.player_from, player_to, action.pos_to, gfi=gfi)
                    gfi = gfi_2  # Switch gfi
                # Use movement
                self.moves += move_needed

            # Block
            Block(self.game, self.home, self.player_from, player_to, action.pos_to, gfi=gfi)

            return False

        elif action.action_type == ActionType.FOUL:

            Foul(self.game, self.home, self.player_from, player_to)

            # A foul is a players last thing to do
            return True

        elif action.action_type == ActionType.PASS:

            # Check distance
            pos_from = self.game.field.get_player_position(self.player_from.player_id)
            pass_distance = self.game.field.pass_distance(pos_from, action.pos_to)

            if self.game.state.weather == WeatherType.BLIZZARD:
                if pass_distance != PassDistance.QUICK_PASS or pass_distance != PassDistance.SHORT_PASS:
                    raise IllegalActionExcpetion("Only quick and short passes during blizzards")

            if pass_distance == PassDistance.HAIL_MARY and not self.player_from.has_skill(Skill.HAIL_MARY):
                raise IllegalActionExcpetion("Hail mary passes requires the Hail Mary skill")

            PassAction(self.game, self.home, self.player_from, pos_from, player_to, action.pos_to, pass_distance)

            self.turn.pass_available = False

    def available_actions(self):
        actions = []
        pos = self.game.state.field.get_player_position(self.player_id)
        if self.player_action_type == PlayerActionType.MOVE:
            move_positions = []
            player_state_from = self.game.state.get_player_state(self.player_id, self.home)
            move_needed = 1 if player_state_from == PlayerState.DOWN_READY else 1
            gif = self.moves + move_needed > self.player_from.get_ma()
            sprints = 3 if self.player_from.has_skill(Skill.SPRINT) else 2
            if player_state_from is PlayerState.DOWN_READY:
                actions.append(ActionChoice(ActionType.STAND_UP, player_ids=[self.player_id], team=self.home))
            elif (not self.turn.quick_snap and self.moves + move_needed <= self.player_from.get_ma() + sprints) or (self.turn.quick_snap and self.moves == 0):
                for square in self.game.state.field.get_adjacent_squares(pos, exclude_occupied=True):
                    move_positions.append(square)
                if len(move_positions) > 0:
                    actions.append(ActionChoice(ActionType.MOVE, player_ids=[self.player_id], team=self.home, positions=move_positions))

        actions.append(ActionChoice(ActionType.END_PLAYER_TURN, team=self.home))
        return actions


class StartGame(Procedure):

    def __init__(self, game):
        super().__init__(game)

    def step(self, action):
        for player in self.game.home.players:
            self.game.state.home_dugout.reserves.append(player.player_id)
        for player in self.game.away.players:
            self.game.state.away_dugout.reserves.append(player.player_id)
        self.game.report(Outcome(OutcomeType.GAME_STARTED))
        return True

    def available_actions(self):
        return [ActionChoice(ActionType.START_GAME, team=None)]


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
        self.done = True

    def step(self, action):
        return False

    def available_actions(self):
        return []


class PreHalf(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.home = home
        self.checked = []

    def step(self, action):
        for player_id, state in self.game.state.get_team_state(self.home).player_states.items():
            if state == PlayerState.KOD and player_id not in self.checked:
                roll = DiceRoll([D6()])
                if roll.get_sum() >= 4:
                    self.game.state.get_team_state(self.home).player_states[player_id] = PlayerState.READY
                    self.game.state.get_dugout(self.home).kod.remove(player_id)
                    self.game.state.get_dugout(self.home).reserves.append(player_id)
                    self.checked.append(player_id)
                    self.game.report(Outcome(OutcomeType.PLAYER_READY, player_id=player_id, rolls=[roll]))
                    return False
                self.checked.append(player_id)
                self.game.report(Outcome(OutcomeType.PLAYER_NOT_READY, player_id=player_id, rolls=[roll]))
                return False
        self.game.state.reset_kickoff()
        return True

    def available_actions(self):
        return []


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

    def available_actions(self):
        return []


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

    def available_actions(self):
        return []


class Scatter(Procedure):

    def __init__(self, game, home, kick=False, is_pass=False, gentle_gust=False):
        super().__init__(game)
        self.home = home  # Having the turn / Kicking team
        self.kick = kick
        self.is_pass = is_pass
        self.gentle_gust = gentle_gust

    def step(self, action):

        # Don't scatter if ball is out
        if self.game.state.field.is_ball_out():
            return True

        # Roll
        roll_scatter = DiceRoll([D8()])
        result_scatter = roll_scatter.get_sum()
        if self.kick and not self.gentle_gust:
            roll_distance = DiceRoll([D6()])
            result_distance = roll_distance.get_sum()

        # Scatter
        x = 0
        y = 0
        if result_scatter in [1, 4, 6]:
            x = -1
        if result_scatter in [3, 5, 9]:
            x = 1
        if result_scatter in [1, 2, 3]:
            y = -1
        if result_scatter in [6, 7, 8]:
            y = 1
        distance = 1 if not self.kick or self.gentle_gust else result_distance

        n = 3 if self.is_pass else 1

        for s in range(n):
            for i in range(distance):
                # Move ball on square
                self.game.state.field.ball_position.x += x
                self.game.state.field.ball_position.y += y

                # Check out of bounds
                if self.kick:
                    if self.game.state.field.is_ball_out():
                        if self.gentle_gust:
                            # Touchback will be enforced after kick-off table when ball lands
                            self.game.report(Outcome(OutcomeType.GENTLE_GUST_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                                     team_home=self.home, rolls=[roll_scatter]))
                        else:
                            # Touchback will be enforced after kick-off table when ball lands
                            self.game.report(Outcome(OutcomeType.KICK_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                                     team_home=self.home, rolls=[roll_scatter, roll_distance]))
                        return True
                    elif self.game.arena.is_team_side(self.game.state.field.ball_position, self.home):
                        if self.gentle_gust:
                            # Touchback will be enforced after kick-off table when ball lands
                            self.game.report(Outcome(OutcomeType.GENTLE_GUST_OPP_HALF, pos=self.game.state.field.ball_position,
                                                     team_home=self.home, rolls=[roll_scatter]))
                        else:
                            # Touchback will be enforced after kick-off table when ball lands
                            self.game.report(Outcome(OutcomeType.KICK_OPP_HALF, pos=self.game.state.field.ball_position,
                                                     team_home=self.home, rolls=[roll_scatter, roll_distance]))
                        return True
                else:
                    # Throw in
                    if self.game.state.field.is_ball_out():
                        # Move ball back
                        self.game.state.field.ball_position.x -= x
                        self.game.state.field.ball_position.y -= y
                        ThrowIn(self.game, self.home, self.game.state.field.ball_position)
                        self.game.report(Outcome(OutcomeType.BALL_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                                 team_home=self.home, rolls=[roll_scatter]))
                        return True

                    # Passes are scattered three times
                    if self.is_pass and x < n-1:
                        continue

                    # On player -> Catch
                    player_id = self.game.state.field.get_player_id_at(self.game.state.field.ball_position)
                    if player_id is not None:
                        Catch(self.game, self.game.get_home_by_player_id(player_id), player_id, self.game.state.field.ball_position)
                        self.game.report(Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.game.state.field.ball_position,
                                                 player_id=player_id, rolls=[roll_scatter]))
                        return True

        if self.kick:
            if self.gentle_gust:
                # Wait for ball to land
                self.game.report(Outcome(OutcomeType.GENTLE_GUST_IN_BOUNDS, pos=self.game.state.field.ball_position, team_home=self.home, rolls=[roll_scatter]))
            else:
                # Wait for ball to land
                self.game.report(Outcome(OutcomeType.KICK_IN_BOUNDS, pos=self.game.state.field.ball_position, team_home=self.home, rolls=[roll_scatter, roll_distance]))
        else:
            # Bounce ball
            Bounce(self.game, self.home)
            self.game.report(Outcome(OutcomeType.BALL_HIT_GROUND, pos=self.game.state.field.ball_position, team_home=self.home, rolls=[roll_scatter]))

        return True

    def available_actions(self):
        return []


class ClearBoard(Procedure):

    def __init__(self, game):
        super().__init__(game)

    def step(self, action):
        self.game.state.field.ball_position = None
        for team in [True, False]:
            for player_id in self.game.get_team(team).get_player_ids():
                # If player not in reserves. move it to it
                if self.game.state.field.get_player_position(player_id) is not None:
                    # Set to ready
                    self.game.state.set_player_state(player_id, team, PlayerState.READY)
                    # Remove from field
                    self.game.state.field.remove(player_id)
                    # Move to reserves
                    self.game.state.get_dugout(team).reserves.append(player_id)
                    # Check if heat exhausted
                    if self.game.state.weather == WeatherType.SWELTERING_HEAT:
                        roll = DiceRoll([D6()])
                        if roll.get_sum() == 1:
                            self.game.state.set_player_state(player_id, team, PlayerState.HEATED)
                            self.game.report(Outcome(OutcomeType.PLAYER_HEATED, player_id=action.player_from_id, rolls=[roll]))
                        self.game.report(Outcome(OutcomeType.PLAYER_NOT_HEATED, player_id=action.player_from_id, rolls=[roll]))
        return True

    def available_actions(self):
        return []


class Setup(Procedure):

    def __init__(self, game, home, reorganize=False):
        super().__init__(game)
        self.home = home
        self.reorganize = reorganize
        self.selected_player = None
        if self.reorganize:
            positions = game.arena.get_team_side(home)
        else:
            positions = game.arena.get_team_side(home) + [None]
        self.aa = [
            ActionChoice(ActionType.PLACE_PLAYER, team=home, player_ids=game.get_team(home).get_player_ids(), positions=positions),
            ActionChoice(ActionType.END_SETUP, team=home),
            ActionChoice(ActionType.AUTO, team=home)
        ]

    def step(self, action):

        if action.action_type == ActionType.AUTO:
            i = 0
            for i in range(min(11, len(self.game.state.get_dugout(self.home).reserves))):
                player_id = self.game.state.get_dugout(self.home).reserves[0]
                y = 3
                x = 13 if self.home else 14
                self.step(Action(ActionType.PLACE_PLAYER, player_from_id=player_id, pos_from=None, pos_to=Square(x, y+i)))
                i += 1
                if i == 11:
                    self.step(Action(ActionType.END_SETUP))
                    break
            return True

        if action.action_type == ActionType.END_SETUP:
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

        if action.action_type == ActionType.PLACE_PLAYER:
            if action.pos_from is None and action.pos_to is None:
                # Move player from reserve to reserve - sure
                return False
            if action.pos_to is None and self.game.arena.is_team_side(action.pos_from, self.home):
                # To reserves
                if self.reorganize:
                    raise IllegalActionExcpetion("You cannot move players to the reserves when reorganizing the defense")
                self.game.state.field.remove(action.player_from_id)
                self.game.state.get_dugout(self.home).reserves.append(action.player_from_id)
            elif action.pos_from is None and self.game.arena.is_team_side(action.pos_to, self.home):
                # From reserves
                if self.reorganize:
                    raise IllegalActionExcpetion("You cannot move players from the reserves when reorganizing the defense")
                self.game.state.get_dugout(self.home).reserves.remove(action.player_from_id)
                self.game.state.field.put(action.player_from_id, action.pos_to)
            elif self.game.arena.is_team_side(action.pos_from, self.home) and self.game.arena.is_team_side(action.pos_to, self.home):
                # Swap players on field
                self.game.state.field.swap(action.pos_from, action.pos_to)
            else:
                raise IllegalActionExcpetion("Unknown placement action")
            self.game.report(Outcome(OutcomeType.PLAYER_PLACED, pos=action.pos_to, player_id=action.player_from_id))
            return False

    def available_actions(self):
        return self.aa


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
        if self.pos.x < 0:  # Above
            y = -1
        elif self.pos.x > len(self.game.arena.board[0]):  # Below
            y = 1
        elif self.pos.y < 0:  # Right
            x = 1
        elif self.pos.y < len(self.game.arena.board[1]):  # Left
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
            self.game.state.field.ball_position.x += x
            self.game.state.field.ball_position.y += y
            if self.game.state.field.is_ball_out():
                # Move ball back
                self.game.state.field.ball_position.x -= x
                self.game.state.field.ball_position.y -= y
                ThrowIn(self.game, self.home, self.game.state.field.ball_position)
                self.game.report(Outcome(OutcomeType.BALL_OUT_OF_BOUNDS, pos=self.game.state.field.ball_position,
                                         team_home=self.home, rolls=[roll_scatter, roll_distance]))
            else:

                # On player -> Catch
                player_id = self.game.state.field.get_player_id_at(self.game.state.field.ball_position)
                if player_id is not None:
                    Catch(self.game, self.game.get_home_by_player_id(player_id), player_id, self.game.state.field.ball_position)
                    self.game.report(Outcome(OutcomeType.BALL_HIT_PLAYER, pos=self.game.state.field.ball_position,
                                             player_id=player_id, rolls=[roll_scatter]))

                # On ground
                else:
                    self.game.report(Outcome(OutcomeType.BALL_ON_GROUND, pos=self.game.state.field.ball_position,
                                             team_home=self.home))

        return True

    def available_actions(self):
        return []


class Turnover(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.home = home

    def step(self, action):
        self.game.report(Outcome(OutcomeType.TURNOVER, team_home=self.home))
        return True

    def available_actions(self):
        return []


class Touchdown(Procedure):

    def __init__(self, game, home, player_id):
        super().__init__(game)
        self.game = game
        self.home = home
        self.player_id = player_id

    def step(self, action):
        self.game.report(Outcome(OutcomeType.TOUCHDOWN, team_home=self.home, player_id=self.player_id))
        self.game.state.get_team_state(self.home).score += 1
        return True

    def available_actions(self):
        return []


class TurnStunned(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.home = home

    def step(self, action):
        players = []
        player_states = self.game.state.get_team_state(self.home).player_states
        for player_id in player_states.keys():
            if player_states[player_id] == PlayerState.STUNNED:
                self.game.state.get_team_state(self.home).player_states[player_id] = PlayerState.DOWN_USED
                players.append(player_id)
        self.game.report(Outcome(OutcomeType.STUNNED_TURNED))
        return True

    def available_actions(self):
        return []


class ResetTurn(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.home = home

    def step(self, action):
        self.game.state.reset_turn(self.home)
        return True

    def available_actions(self):
        return []


class Turn(Procedure):

    def __init__(self, game, home, half, turn, blitz=False, quick_snap=False):
        super().__init__(game)
        self.home = home
        self.half = half
        self.turn = turn
        self.blitz = blitz
        self.quick_snap = quick_snap
        self.blitz_available = not quick_snap
        self.pass_available = not quick_snap
        self.handoff_available = not quick_snap
        self.foul_available = not quick_snap
        TurnStunned(self.game, self.home)
        ResetTurn(self.game, self.home)

    def start_player_action(self, outcome_type, player_action_type, player_id):

        # Start action
        PlayerAction(self.game, self.home, player_id, player_action_type, turn=self)
        self.game.report(Outcome(outcome_type, player_id=player_id))
        return False

    def step(self, action):

        # Handle End Turn action
        if action.action_type == ActionType.END_TURN:
            if self.blitz:
                self.game.report(Outcome(OutcomeType.END_OF_BLITZ, team_home=self.home))
            elif self.quick_snap:
                self.game.report(Outcome(OutcomeType.END_OF_QUICK_SNAP, team_home=self.home))
            else:
                self.game.report(Outcome(OutcomeType.END_OF_TURN, team_home=self.home))
            return True

        # Start movement action
        if action.action_type == ActionType.START_MOVE:
            return self.start_player_action(OutcomeType.MOVE_ACTION_STARTED, PlayerActionType.MOVE, action.player_from_id)

        # Start blitz action
        if action.action_type == ActionType.START_BLITZ:
            self.blitz_available = False
            return self.start_player_action(OutcomeType.BLITZ_ACTION_STARTED, PlayerActionType.BLITZ, action.player_from_id)

        # Start foul action
        if action.action_type == ActionType.START_FOUL:
            self.foul_available = False
            return self.start_player_action(OutcomeType.FOUL_ACTION_STARTED, PlayerActionType.FOUL, action.player_from_id)

        # Start block action
        if action.action_type == ActionType.START_BLOCK:
            return self.start_player_action(OutcomeType.BLOCK_ACTION_STARTED, PlayerActionType.BLOCK, action.player_from_id)

        # Start pass action
        if action.action_type == ActionType.START_PASS:
            self.pass_available = False
            return self.start_player_action(OutcomeType.PASS_ACTION_STARTED, PlayerActionType.PASS, action.player_from_id)

        # Start handoff action
        if action.action_type == ActionType.START_HANDOFF:
            self.handoff_available = False
            return self.start_player_action(OutcomeType.HANDOFF_ACTION_STARTED, PlayerActionType.HANDOFF, action.player_from_id)

    def available_actions(self):
        move_player_ids = []
        block_player_ids = []
        blitz_player_ids = []
        pass_player_ids = []
        handoff_player_ids = []
        foul_player_ids = []
        for player_id, player_state in self.game.state.get_team_state(self.home).player_states.items():
            pos = self.game.state.field.get_player_position(player_id)
            if pos is None:
                continue
            if self.blitz:
                if self.game.state.field.get_tackle_zones(pos, home=self.home) > 0:
                    continue
            if player_state == PlayerState.READY or player_state == PlayerState.DOWN_READY:
                move_player_ids.append(player_id)
                if self.blitz_available:
                    blitz_player_ids.append(player_id)
                if self.pass_available:
                    pass_player_ids.append(player_id)
                if self.handoff_available:
                    handoff_player_ids.append(player_id)
                if self.foul_available:
                    foul_player_ids.append(player_id)
            if player_state == PlayerState.READY:
                block_player_ids.append(player_id)

        actions = []
        if len(move_player_ids) > 0:
            actions.append(ActionChoice(ActionType.START_MOVE, team=self.home, player_ids=move_player_ids))
        if len(block_player_ids) > 0:
            actions.append(ActionChoice(ActionType.START_BLOCK, team=self.home, player_ids=block_player_ids))
        if len(blitz_player_ids) > 0:
            actions.append(ActionChoice(ActionType.START_BLITZ, team=self.home, player_ids=blitz_player_ids))
        if len(pass_player_ids) > 0:
            actions.append(ActionChoice(ActionType.START_PASS, team=self.home, player_ids=pass_player_ids))
        if len(handoff_player_ids) > 0:
            actions.append(ActionChoice(ActionType.START_HANDOFF, team=self.home, player_ids=handoff_player_ids))
        if len(foul_player_ids) > 0:
            actions.append(ActionChoice(ActionType.START_FOUL, team=self.home, player_ids=foul_player_ids))
        actions.append(ActionChoice(ActionType.END_TURN, team=self.home))

        return actions


class WeatherTable(Procedure):

    def __init__(self, game, kickoff=False):
        super().__init__(game)
        self.kickoff = kickoff

    def step(self, action):
        roll = DiceRoll([D6(), D6()])
        if roll.get_sum() == 2:
            self.game.state.weather = WeatherType.SWELTERING_HEAT
            self.game.report(Outcome(OutcomeType.WEATHER_SWELTERING_HEAT, rolls=[roll]))
        if roll.get_sum() == 3:
            self.game.state.weather = WeatherType.VERY_SUNNY
            self.game.report(Outcome(OutcomeType.WEATHER_VERY_SUNNY, rolls=[roll]))
        if 4 <= roll.get_sum() <= 10:
            self.game.state.weather = WeatherType.NICE
            if self.kickoff:
                self.game.state.gentle_gust = True
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
