from procs.procedure import Procedure
from model.action import Action, ActionType
from model.outcome import Outcome, OutcomeType
from model.dice import DiceRoll, D6, D3
from model.player import PlayerState
from procs.weather import Weather
from procs.setup import Setup
from procs.turn import Turn
from procs.knock_down import KnockDown


class GetTheRef(Procedure):
    '''
    Each team receives 1 additional Bribe to use during this game.
    '''
    def __init__(self, game, home):
        self.game = game
        self.home = home  # Receiving team
        super().__init__()

    def step(self, action):
        self.game.state.home_state.bribes += 1
        self.game.state.away_state.bribes += 1
        return Outcome(OutcomeType.GET_THE_REF), False


class Riot(Procedure):
    '''
    The trash talk between two opposing players explodes and rapidly degenerates, involving the rest of the players.
    If the receiving team’s turn marker is on turn 7 for the half, both teams move their turn marker back one space as
    the referee resets the clock back to before the fight started. If the receiving team has not yet taken a turn this
    half the referee lets the clock run on during the fight and both teams’ turn markers are moved forward one space.
    Otherwise roll a D6. On a 1-3, both teams’ turn markers are moved forward one space. On a 4-6, both team’s turn
    markers are moved back one space.
    '''
    def __init__(self, game, home):
        self.game = game
        self.home = home  # Kicking team
        super().__init__()

    def step(self, action):
        roll = None
        if self.game.state.get_team_state(not self.home).turn == 7:
            n = -1
        elif self.game.state.get_team_state(not self.home).turn == 0:
            n = 1
        else:
            roll = DiceRoll([D6()])
            if roll.get_sum() <= 3:
                n = 1
            else:
                n = -11

        self.game.state.get_team_state(self.home).turn += n
        self.game.state.get_team_state(not self.home).turn += n
        return Outcome(OutcomeType.RIOT, n=n, rolls=[roll]), True


class HighKick(Procedure):
    '''
    High Kick: The ball is kicked very high, allowing a player on the receiving team time to move into the
    perfect position to catch it. Any one player on the receiving team who is not in an opposing player’s
    tackle zone may be moved into the square where the ball will land no matter what their MA may be, as long
    as the square is unoccupied.
    '''
    def __init__(self, game, home):
        self.game = game
        self.home = home  # Receiving team
        super().__init__()

    def step(self, action):
        assert action in [ActionType.PLACE_PLAYER, ActionType.END_SETUP] and action.pos_to is not None
        if action.action_type == ActionType.PLACE_PLAYER:
            if self.game.arena.is_team_side(action.pos_to, self.home) and \
                    np.array_equal(self.game.state.field.ball_position, action.pos_to) and \
                    self.game.state.field.get_player_id_at(action.pos_to) is None:
                self.game.state.field.move(action.player_from_id, action.pos_to)
                return Outcome(OutcomeType.PLAYER_PLACED, pos=action.pos_to, team_home=self.home), True
            else:
                return Outcome(OutcomeType.NOT_ALLOWED, pos=action.pos_to, team_home=self.home), False
        elif action.action_type == ActionType.END_SETUP:
            return Outcome(OutcomeType.SETUP_DONE, team_home=self.home), True


class CheeringFans(Procedure):
    '''
    Each coach rolls a D3 and adds their team’s FAME (see page 18) and the number of cheerleaders on their team to the
    score. The team with the highest score is inspired by their fans' cheering and gets an extra re-roll this half.
    If both teams have the same score, then both teams get a re-roll.
    '''
    def __init__(self, game):
        self.game = game
        self.home = home  # Kicking team
        super().__init__()

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

        return Outcome(OutcomeType.CHEERING_FANS, rolls=[roll_home, roll_away])


class BrilliantCoaching(Procedure):
    '''
    Each coach rolls a D3 and adds their FAME (see page 18) and the number of assistant coaches on their team to the
    score. The team with the highest total gets an extra team re-roll this half thanks to the brilliant instruction
    provided by the coaching staff. In case of a tie both teams get an extra team re-roll.
    '''
    def __init__(self, game):
        self.game = game
        self.home = home  # Kicking team
        super().__init__()

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

        return Outcome(OutcomeType.BRILLIANT_COACHING, rolls=[roll_home, roll_away])


class ThrowARock(Procedure):
    '''
    An enraged fan hurls a large rock at one of the players on the opposing team. Each coach rolls a D6 and adds their
    FAME (see page 18) to the roll. The fans of the team that rolls higher are the ones that threw the rock. In the
    case of a tie a rock is thrown at each team! Decide randomly which player in the other team was hit (only players
    on the pitch are eligible) and roll for the effects of the injury straight away. No Armour roll is required.
    '''
    def __init__(self, game):
        self.game = game
        self.procedures = []
        self.rolled = False
        super().__init__()

    def step(self, action):
        if self.rolled:
            outcome, terminal = self.procedures[0].step(action)
            if outcome.terminal:
                self.procedures.pop()
                if len(self.procedures) == 0:
                    return outcome, True
            return outcome, False
        else:
            roll_home = DiceRoll([D6()])
            roll_away = DiceRoll([D6()])

            rh = roll_home.get_sum() + self.game.state.home_state.fame
            ra = roll_away.get_sum() + self.game.state.away_state.fame

            if rh >= ra:
                player_away_id = self.game.state.field.get_random_player(True)
                pos = self.game.state.field.get_player_position(player_away_id)
                self.procedures.insert(0, KnockDown(self.game, False, player_away_id, pos, armor_roll=False))
            if ra >= rh:
                player_home_id = self.game.state.field.get_random_player(False)
                pos = self.game.state.field.get_player_position(player_home_id)
                self.procedures.insert(0, KnockDown(self.game, True, player_home_id, pos, armor_roll=False))

            return Outcome(OutcomeType.THROW_A_ROCK, rolls=[roll_home, roll_away]), False


class PitchInvasionRoll(Procedure):
    '''
    ... If a roll is 6 or more after modification then the player is Stunned (players with the Ball & Chain skill are
    KO'd). A roll of 1 before adding FAME will always have no effect.
    '''
    def __init__(self, game, home, player_id):
        self.game = game
        self.home = home
        self.player_id = player_id
        super().__init__()

    def step(self, action):
        roll = DiceRoll([D6()])

        roll.modifiers = self.game.state.home_state.fame
        result = roll.get_sum() + roll.modifiers

        if result >= 6:
            self.game.state.get_home_state(self.home).player_states[self.player_id] = PlayerState.STUNNED
            # TODO: Ball and Chain

        return Outcome(OutcomeType.PITCH_INVASION_ROLL, rolls=[roll]), True


class KickOffTable(Procedure):

    def __init__(self, game, home):
        self.game = game
        self.home = home
        self.rolled = False
        self.procedures = []
        super().__init__()

    def step(self, action):

        if self.rolled:
            outcome, terminal = self.procedures[0].step(action)
            if outcome.terminal:
                self.procedures.pop()
                if len(self.procedures) == 0:
                    return outcome, True
            return outcome, False
        else:
            roll = DiceRoll([D6(), D6()])
            result = roll.get_sum()

            self.rolled = True

            if result == 2:  # Get the ref!
                self.procedures.insert(0, GetTheRef(self.game, self.home))
                return Outcome(OutcomeType.KICKOFF_GET_THE_REF, rolls=[roll]), False
            elif result == 3:  # Riot!
                self.procedures.insert(0, Riot(self.game, self.home))
                return Outcome(OutcomeType.KICKOFF_RIOT, rolls=[roll]), False
            elif result == 4:  # Perfect defense
                self.procedures.insert(0, Setup(self.game, home=self.home, reorganize=True))
                return Outcome(OutcomeType.KICKOFF_PERFECT_DEFENSE, team_home=self.home, rolls=[roll]), False
            elif result == 5:  # High Kick
                self.procedures.insert(0, HighKick(self.game, home=not self.home))
                return Outcome(OutcomeType.KICKOFF_HIGH_KICK, rolls=[roll]), False
            elif result == 6:  # Cheering fans
                self.procedures.insert(0, CheeringFans(self.game))
                return Outcome(OutcomeType.KICKOFF_CHEERING_FANS, rolls=[roll])
            elif result == 7:  # Changing Weather
                self.procedures.insert(0, Weather(self.game, kickoff=True))
                return Outcome(OutcomeType.KICKOFF_CHANGING_WHEATHER, rolls=[roll])
            elif result == 8:  # Brilliant Coaching
                self.procedures.insert(0, BrilliantCoaching(self.game))
                return Outcome(OutcomeType.KICKOFF_BRILLIANT_COACHING, rolls=[roll]), False
            elif result == 9:  # Quick Snap
                self.procedures.insert(0, Turn(self.game, not self.home, quick_snap=True))
                return Outcome(OutcomeType.KICKOFF_QUICK_SNAP, rolls=[roll]), False
            elif result == 10:  # Blitz
                self.procedures.insert(0, Turn(self.game, self.home, blitz=True))
                return Outcome(OutcomeType.KICKOFF_BLITZ, rolls=[roll]), False
            elif result == 11:  # Throw a Rock
                self.procedures.insert(0, ThrowARock(self.game))
                return Outcome(OutcomeType.KICKOFF_THROW_A_ROCK, rolls=[roll]), False
            elif result == 12:  # Pitch Invasion
                for player_id in self.game.state.field.get_team_player_ids(True):
                    self.procedures.insert(0, PitchInvasionRoll(self.game, True, player_id))
                for player_id in self.game.state.field.get_team_player_ids(False):
                    self.procedures.insert(0, PitchInvasionRoll(self.game, False, player_id))
                return Outcome(OutcomeType.KICKOFF_PITCH_INVASION, rolls=[roll]), False



