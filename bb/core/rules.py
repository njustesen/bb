from core import CasualtyType, CasualtyEffect
from model import PlayerState, PassDistance
from enum import Enum


class PassDistance(Enum):
    QUICK_PASS = 1
    SHORT_PASS = 2
    LONG_PASS = 3
    LONG_BOMB = 4
    HAIL_MARY = 5


class Rules:

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
