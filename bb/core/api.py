from bb.core.host import *
from bb.core.game import *
from bb.core.load import *

host = Host()


def new_game(home_name="reikland_reivers", away_name="gouged_eye", config_name="bb.json"):
    config = get_config(config_name)
    arena = get_arena(config.arena)
    ruleset = get_rule_set(config.ruleset)
    home = get_team(home_name, ruleset)
    away = get_team(away_name, ruleset)
    game_id = str(uuid.uuid1())
    game = Game(game_id, home, away, arena, config)
    game.init()
    host.add_game(game)
    print("Game created with id ", game.game_id)
    return game


def step(game_id, action):
    game = host.get_game(game_id)
    done = False
    while not done:
        done = game.step(action)
        if done and not game.config.fast_mode:
            break
        action = None
    if game.stack.is_empty():
        host.end_game(game_id)
    return game


def get_game(game_id):
    return host.get_game(game_id)


def get_games():
    return host.get_games()
