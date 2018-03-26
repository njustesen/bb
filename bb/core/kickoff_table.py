from core import Procedure, Weather, Setup, Turn
from model import ActionType, Outcome, OutcomeType, DiceRoll, D6, D3, PlayerState, KnockDown, Skill
from exception import IllegalActionExcpetion
import numpy as np


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


class Riot(Procedure):
    """
    The trash talk between two opposing players explodes and rapidly degenerates, involving the rest of the players.
    If the receiving team’s turn marker is on turn 7 for the half, both teams move their turn marker back one space as
    the referee resets the clock back to before the fight started. If the receiving team has not yet taken a turn this
    half the referee lets the clock run on during the fight and both teams’ turn markers are moved forward one space.
    Otherwise roll a D6. On a 1-3, both teams’ turn markers are moved forward one space. On a 4-6, both team’s turn
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
        self.game.report(Outcome(OutcomeType.RIOT, n=self.effect, rolls=[roll]))
        return True


class HighKick(Procedure):
    """
    High Kick: The ball is kicked very high, allowing a player on the receiving team time to move into the
    perfect position to catch it. Any one player on the receiving team who is not in an opposing player’s
    tackle zone may be moved into the square where the ball will land no matter what their MA may be, as long
    as the square is unoccupied.
    """
    def __init__(self, game, home):
        super().__init__(game)
        self.home = home  # Receiving team

    def step(self, action):
        if action.action_type == ActionType.PLACE_PLAYER:
            if self.game.arena.is_team_side(action.pos_to, self.home) and \
                    np.array_equal(self.game.state.field.ball_position, action.pos_to) and \
                    self.game.state.field.get_player_id_at(action.pos_to) is None:
                self.game.state.field.move(action.player_from_id, action.pos_to)
                self.game.report(Outcome(OutcomeType.PLAYER_PLACED, pos=action.pos_to, team_home=self.home))
            else:
                raise IllegalActionExcpetion("Illegal position")
        elif action.action_type == ActionType.END_SETUP:
            self.game.report(Outcome(OutcomeType.SETUP_DONE, team_home=self.home))
        return True


class CheeringFans(Procedure):
    """
    Each coach rolls a D3 and adds their team’s FAME (see page 18) and the number of cheerleaders on their team to the
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
        if ra >= rh:
            self.game.state.away_state.rerolls += 1

        self.game.report(Outcome(OutcomeType.CHEERING_FANS, rolls=[roll_home, roll_away]))
        return True


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
        if ra >= rh:
            self.game.state.away_state.rerolls += 1

        self.game.report(Outcome(OutcomeType.BRILLIANT_COACHING, rolls=[roll_home, roll_away]))
        return True


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

            if rh >= ra:
                player_away_id = self.game.state.field.get_random_player(True)
                KnockDown(self.game, False, player_away_id, armor_roll=False)
            if ra >= rh:
                player_home_id = self.game.state.field.get_random_player(False)
                KnockDown(self.game, True, player_home_id, armor_roll=False)

            return Outcome(OutcomeType.THROW_A_ROCK, rolls=[roll_home, roll_away]), False


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

        roll.modifiers = self.game.state.home_state.fame
        result = roll.get_sum() + roll.modifiers

        if result >= 6:
            if self.game.get_player(self.player_id).has_skill(Skill.BALL_AND_CHAIN):
                self.game.report(Outcome(OutcomeType.PITCH_INVASION_ROLL, rolls=[roll], player_id=self.player_id, team_home=self.home))
                KnockedOut(self.game, self.home, self.player_id)
            else:
                self.game.state.set_player_state(self.player_id, self.home, PlayerState.STUNNED)
                self.game.report(Outcome(OutcomeType.PITCH_INVASION_ROLL, rolls=[roll], player_id=self.player_id, team_home=self.home, n=PlayerState.STUNNED))
        else:
            self.game.report(Outcome(OutcomeType.PITCH_INVASION_ROLL, rolls=[roll], player_id=self.player_id, team_home=self.home, n=PlayerState.READY))

        return True


class KickOffTable(Procedure):

    def __init__(self, game, home):
        super().__init__(game)
        self.home = home
        self.rolled = False

    def step(self, action):

        roll = DiceRoll([D6(), D6()])
        result = roll.get_sum()

        self.rolled = True

        if result == 2:  # Get the ref!
            GetTheRef(self.game, self.home)
            self.game.report(Outcome(OutcomeType.KICKOFF_GET_THE_REF, rolls=[roll]))
        elif result == 3:  # Riot!
            Riot(self.game, self.home)
            self.game.report(Outcome(OutcomeType.KICKOFF_RIOT, rolls=[roll]))
        elif result == 4:  # Perfect defense
            Setup(self.game, home=self.home, reorganize=True)
            self.game.report(Outcome(OutcomeType.KICKOFF_PERFECT_DEFENSE, team_home=self.home, rolls=[roll]))
        elif result == 5:  # High Kick
            HighKick(self.game, home=not self.home)
            self.game.report(Outcome(OutcomeType.KICKOFF_HIGH_KICK, rolls=[roll]))
        elif result == 6:  # Cheering fans
            CheeringFans(self.game)
            self.game.report(Outcome(OutcomeType.KICKOFF_CHEERING_FANS, rolls=[roll]))
        elif result == 7:  # Changing Weather
            Weather(self.game, kickoff=True)
            self.game.report(Outcome(OutcomeType.KICKOFF_CHANGING_WHEATHER, rolls=[roll]))
        elif result == 8:  # Brilliant Coaching
            BrilliantCoaching(self.game)
            self.game.report(Outcome(OutcomeType.KICKOFF_BRILLIANT_COACHING, rolls=[roll]))
        elif result == 9:  # Quick Snap
            Turn(self.game, not self.home, quick_snap=True)
            self.game.report(Outcome(OutcomeType.KICKOFF_QUICK_SNAP, rolls=[roll]))
        elif result == 10:  # Blitz
            Turn(self.game, self.home, blitz=True)
            self.game.report(Outcome(OutcomeType.KICKOFF_BLITZ, rolls=[roll]))
        elif result == 11:  # Throw a Rock
            ThrowARock(self.game)
            self.game.report(Outcome(OutcomeType.KICKOFF_THROW_A_ROCK, rolls=[roll]))
        elif result == 12:  # Pitch Invasion
            for player_id in self.game.state.field.get_team_player_ids(True):
                PitchInvasionRoll(self.game, True, player_id)
            for player_id in self.game.state.field.get_team_player_ids(False):
                PitchInvasionRoll(self.game, False, player_id)
            self.game.report(Outcome(OutcomeType.KICKOFF_PITCH_INVASION, rolls=[roll]))

        return True



