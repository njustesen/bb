import uuid
from bb.core.host import *
from bb.core.game import *
from bb.core.load import *

# Create a game host
ruleset = get_rule_set("LRB5-Experimental.xml")
host = Host(ruleset)

# Add all saved games to host
saved_game_files = [game for game in host.get_saved_games()]
for file in saved_game_files:
    host.add_game(host.load_game(file))


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

    # Run until user input is required
    while True:
        done = game.step(action)
        if done or not game.config.fast_mode:
            break
        action = None

    # If game is over
    if game.game_over:
        host.end_game(game_id)

    return game


def save_game(game_id):
    host.save_game(game_id)


def get_game(game_id):
    return host.get_game(game_id)


def get_games():
    return host.get_games()


def get_teams():
    return get_all_teams(host.ruleset)


# Initialize with one game
new_game("a1", "b2")
