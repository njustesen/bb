import uuid
from bb.core.host import *
from bb.core.game import *
from bb.core.load import *

ruleset = get_rule_set("LRB5-Experimental.xml")
host = Host(ruleset)


def new_game(home_team_id, away_team_id, config_name="bb.json"):
    config = get_config(config_name)
    arena = get_arena(config.arena)
    ruleset = get_rule_set(config.ruleset)
    home = get_team_by_id(home_team_id, ruleset)
    away = get_team_by_id(away_team_id, ruleset)
    game_id = str(uuid.uuid1())
    game = Game(game_id, home, away, arena, config)
    game.init()
    host.add_game(game)
    print("Game created with id ", game.game_id)
    return game


def step(game_id, action):
    game = host.get_game(game_id)
    game.step(action)
    if game.game_over:
        host.end_game(game_id)
    return game


def get_game(game_id):
    return host.get_game(game_id)


def get_games():
    return host.get_games()


def get_teams():
    return get_all_teams(host.ruleset)
