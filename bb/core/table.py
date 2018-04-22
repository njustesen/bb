from enum import Enum


class Tile(Enum):
    HOME = 1
    HOME_TOUCHDOWN = 2
    HOME_WING_LEFT = 3
    HOME_WING_RIGHT = 4
    HOME_SCRIMMAGE = 5
    AWAY = 6
    AWAY_TOUCHDOWN = 7
    AWAY_WING_LEFT = 8
    AWAY_WING_RIGHT = 9
    AWAY_SCRIMMAGE = 10
    CROWD = 11


class BBDieResult(Enum):
    ATTACKER_DOWN = 1
    BOTH_DOWN = 2
    PUSH = 3
    DEFENDER_STUMBLES = 4
    DEFENDER_DOWN = 5


class OutcomeType(Enum):
    HEADS_WON = 1
    HEADS_LOSS = 2
    WEATHER_SWELTERING_HEAT = 3
    WEATHER_VERY_SUNNY = 4
    WEATHER_NICE = 5
    WEATHER_POURING_RAIN = 6
    WEATHER_BLIZZARD = 7
    PLAYER_PLACED = 9
    ILLEGAL_SETUP_NUM = 10
    ILLEGAL_SETUP_SCRIMMAGE = 11
    ILLEGAL_SETUP_WINGS = 12
    BALL_PLACED = 13
    KICKOFF_GET_THE_REF = 14
    KICKOFF_RIOT = 15
    KICKOFF_PERFECT_DEFENSE = 16
    KICKOFF_HIGH_KICK = 17
    KICKOFF_CHEERING_FANS = 18
    KICKOFF_CHANGING_WHEATHER = 19
    KICKOFF_BRILLIANT_COACHING = 20
    KICKOFF_QUICK_SNAP = 21
    KICKOFF_BLITZ = 22
    KICKOFF_THROW_A_ROCK = 23
    KICKOFF_PITCH_INVASION = 24
    GET_THE_REF = 25
    RIOT = 26
    HIGH_KICK = 27
    CHEERING_FANS = 28
    BRILLIANT_COACHING = 29
    THROW_A_ROCK = 30
    PITCH_INVASION = 31
    PITCH_INVASION_ROLL = 32
    NOTHING = 33
    KICK_IN_BOUNDS = 34
    KICK_OUT_OF_BOUNDS = 35
    BALL_HIT_GROUND = 36
    BALL_HIT_PLAYER = 37
    SETUP_DONE = 38
    KNOCKED_DOWN = 39
    ARMOR_BROKEN = 40
    ARMOR_NOT_BROKEN = 41
    STUNNED = 42
    KNOCKED_OUT = 43
    BADLY_HURT = 44
    INTERCEPTION = 46
    BALL_CAUGhT = 47
    BALL_DROPPED = 48
    FAILED_DODGE = 49
    SUCCESSFUL_DODGE = 50
    FAILED_GFI = 51
    SUCCESSFUL_GFI = 52
    FAILED_PICKUP = 53
    SUCCESSFUL_PICKUP = 54
    COMPLETE_PASS = 55
    INCOMPLETE_PASS = 56
    COMPLETE_HANDOFF = 57
    INCOMPLETE_HANDOFF = 58
    STUNNED_TURNED = 59
    END_PLAYER_TURN = 60
    MOVE_ACTION_STARTED = 61
    BLOCK_ACTION_STARTED = 62
    BLITZ_ACTION_STARTED = 63
    PASS_ACTION_STARTED = 64
    FOUL_ACTION_STARTED = 65
    HANDOFF_ACTION_STARTED = 66
    END_OF_GAME = 67
    END_OF_PREGAME = 68
    END_OF_TURN = 69
    END_OF_HALF = 70
    TOUCHDOWN = 71
    TURNOVER = 72
    CASUALTY = 73
    APOTHECARY_USED_KO = 74
    APOTHECARY_USED_CASUALTY = 75
    CASUALTY_APOTHECARY = 76
    DAUNTLESS_USED = 77
    PUSHED_INTO_CROWD = 78
    PUSHED = 79
    ACCURATE_PASS = 80
    INACCURATE_PASS = 81
    FUMBLE = 82
    CATCH_FAILED = 83
    HOME_RECEIVE = 84
    AWAY_RECEIVE = 85
    TAILS_WON = 86
    TAILS_LOSS = 87
    TOUCHBACK = 88
    BALL_ON_GROUND = 89
    GAME_STARTED = 90
    BALL_SCATTER = 91
    SPECTATORS = 92
    FAME = 93


class PlayerActionType(Enum):
    MOVE = 1
    BLOCK = 2
    BLITZ = 3
    PASS = 4
    HANDOFF = 5
    FOUL = 7


class PlayerState(Enum):
    READY = 1
    USED = 2
    DOWN_READY = 3
    DOWN_USED = 4
    STUNNED = 5
    KOD = 6
    BH = 7
    MNG = 8
    DEAD = 9
    BONE_HEADED = 10
    HYPNOTIZED = 11
    REALLY_STUPID = 12
    HEATED = 13
    EJECTED = 14


class CasualtyEffect(Enum):
    NONE = 1
    MNG = 2
    NI = 3
    MA = 4
    AV = 5
    AG = 6
    ST = 7
    DEAD = 8


class CasualtyType(Enum):
    """
    D68 Result Effect
    11-38 Badly Hurt No long term effect
    41 Broken Ribs Miss next game
    42 Groin Strain Miss next game
    43 Gouged Eye Miss next game
    44 Broken Jaw Miss next game
    45 Fractured Arm Miss next game
    46 Fractured Leg Miss next game
    47 Smashed Hand Miss next game
    48 Pinched Nerve Miss next game
    51 Damaged Back Niggling Injury
    52 Smashed Knee Niggling Injury
    53 Smashed Hip -1 MA
    54 Smashed Ankle -1 MA
    55 Serious Concussion -1 AV
    56 Fractured Skull -1 AV
    57 Broken Neck -1 AG
    58 Smashed Collar Bone -1 ST
    61-68 DEAD Dead!
    """
    BADLY_HURT = 38
    BROKEN_RIBS = 41
    GROIN_STRAIN = 42
    GOUGED_EYE = 43
    BROKEN_JAW = 44
    FRACTURED_ARM = 45
    FRACTURED_LEG = 46
    SMASHED_HAND = 47
    PINCHED_NERVE = 48
    DAMAGED_BACK = 51
    SMASHED_KNEE = 52
    SMASHED_HIP = 53
    SMASHED_ANKLE = 54
    SERIOUS_CONCUSSION = 55
    FRACTURED_SKULL = 56
    BROKEN_NECK = 57
    SMASHED_COLLAR_BONE = 58
    DEAD = 61


class ActionType(Enum):
    START_GAME = 1
    END_GAME = 2
    HEADS = 3
    TAILS = 4
    KICK = 5
    RECEIVE = 6
    PLACE_PLAYER = 7
    END_SETUP = 8
    PLACE_BALL = 9
    START_MOVE = 10
    START_BLOCK = 11
    START_BLITZ = 12
    START_PASS = 13
    START_FOUL = 14
    START_HANDOFF = 15
    END_PLAYER_TURN = 16
    MOVE = 17
    BLOCK = 18
    BLITZ = 19
    PASS = 20
    FOUL = 21
    HANDOFF = 22
    USE_SKILL = 23
    USE_REROLL = 24
    END_TURN = 25
    SELECT_DIE = 26
    USE_APOTHECARY = 27
    USE_ROLL = 28
    USE_JUGGERNAUT = 29
    USE_WRESTLE = 30
    DONT_USE_SKILL = 31
    FOLLOW_UP = 32
    DONT_FOLLOW_UP = 33
    INTERCEPTION = 34
    CONTINUE = 35
    ROLL_FOR_WEATHER = 36
    SELECT_PLAYER = 37
    SELECT_NONE = 38


class WeatherType(Enum):
    SWELTERING_HEAT = 1
    VERY_SUNNY = 2
    NICE = 3
    POURING_RAIN = 4
    BLIZZARD = 5


class SkillCategory(Enum):
    General = 0,
    Agility = 1,
    Strength = 2,
    Passing = 3,
    Mutation = 4,
    Extraordinary = 5


class Skill(Enum):
    THICK_SKULL = 1
    STUNTY = 2
    MIGHTY_BLOW = 3
    CLAWS = 4
    SPRINT = 5
    SURE_FEET = 6
    NO_HANDS = 7
    BALL_AND_CHAIN = 8
    DODGE = 9
    PREHENSILE_TAIL = 10
    TACKLE = 11
    BREAK_TACKLE = 12
    TITCHY = 13
    DIVING_TACKLE = 14
    SHADOWING = 15
    TENTACLES = 16
    TWO_HEADS = 17
    BLOCK = 18
    WRESTLE = 19
    STAND_FIRM = 20
    GUARD = 21
    HORNS = 22
    SIDE_STEP = 23
    FRENZY = 24
    CATCH = 25
    SURE_HANDS = 26
    BIG_HAND = 27
    EXTRA_ARMS = 28
    DIRTY_PLAYER = 29
    SNEAKY_GIT = 30
    STRONG_ARM = 31
    LONG_LEGS = 32
    PASS = 33
    LONER = 34
    WILD_ANIMAL = 35
    RIGHT_STUFF = 36
    ALWAYS_HUNGRY = 37
    REALLY_STUPID = 36
    REGENERATION = 37
    THROW_TEAM_MATE = 38
    BONE_HEAD = 39
    DUMP_OFF = 40
    STAB = 41
    JUMP_UP = 42
    DAUNTLESS = 43
    JUGGERNAUT = 44
    SECRET_WEAPON = 45
    NERVES_OF_STEEL = 46
    BOMBARDIER = 47
    LEAP = 48
    VERY_LONG_LEGS = 49
    CHAINSAW = 50
    TAKE_ROOT = 51
    SAFE_THROW = 52
    DECAY = 53
    DISTURBING_PRESENCE = 54
    NURGLES_ROT = 55
    FOUL_APPEARANCE = 56
    DIVING_CATCH = 57
    BLOOD_LUST = 58
    HYPNOTIC_GAZE = 59
    HAIL_MARY_PASS = 60
    ACCURATE = 61
    KICK = 62
    KICK_OFF_RETURN = 63
    PASS_BLOCK = 64
    FEND = 65
    MULTIPLE_BLOCK = 66
    STRIP_BALL = 67
    GRAB = 68
    STAKES = 69


class PassDistance(Enum):
    QUICK_PASS = 1
    SHORT_PASS = 2
    LONG_PASS = 3
    LONG_BOMB = 4
    HAIL_MARY = 5


class Rules:

    ready_to_catch = [PlayerState.READY, PlayerState.USED]

    pass_modifiers = {
        PassDistance.QUICK_PASS: 1,
        PassDistance.SHORT_PASS: 0,
        PassDistance.LONG_PASS: -1,
        PassDistance.LONG_BOMB: -2,
        PassDistance.HAIL_MARY: 0  # Not used
    }

    casualty_effect = {
        CasualtyType.BADLY_HURT: CasualtyEffect.NONE,
        CasualtyType.BROKEN_RIBS: CasualtyEffect.MNG,
        CasualtyType.GROIN_STRAIN: CasualtyEffect.MNG,
        CasualtyType.GOUGED_EYE: CasualtyEffect.MNG,
        CasualtyType.BROKEN_JAW: CasualtyEffect.MNG,
        CasualtyType.FRACTURED_ARM: CasualtyEffect.MNG,
        CasualtyType.FRACTURED_LEG: CasualtyEffect.MNG,
        CasualtyType.SMASHED_HAND: CasualtyEffect.MNG,
        CasualtyType.PINCHED_NERVE: CasualtyEffect.MNG,
        CasualtyType.DAMAGED_BACK: CasualtyEffect.NI,
        CasualtyType.SMASHED_KNEE: CasualtyEffect.NI,
        CasualtyType.SMASHED_HIP: CasualtyEffect.MA,
        CasualtyType.SMASHED_ANKLE: CasualtyEffect.MA,
        CasualtyType.SERIOUS_CONCUSSION: CasualtyEffect.AV,
        CasualtyType.FRACTURED_SKULL: CasualtyEffect.AV,
        CasualtyType.BROKEN_NECK: CasualtyEffect.AG,
        CasualtyType.SMASHED_COLLAR_BONE: CasualtyEffect.ST,
        CasualtyType.DEAD: CasualtyEffect.DEAD
    }

    has_tackle_zone = {
        PlayerState.READY,
        PlayerState.USED
    }
