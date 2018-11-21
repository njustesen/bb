from gym.envs.registration import registry, register, make, spec
from bb.core.load import *

ruleset = get_rule_set('LRB5-Experimental.xml')

register(
    id='FFAI-v1',
    entry_point='bb.ai.env:FFAIEnv',
    kwargs={'config': get_config("ff-gym.json"),
            'home_team': get_team('human-1', ruleset),
            'away_team': get_team('human-2', ruleset)
            }
)
