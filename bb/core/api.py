import uuid
from bb.core.host import *
from bb.core.game import *
from bb.core.load import *

# Create a game host
host = Host()


def new_game(home_team_id, away_team_id, config_name="ff.json"):
    config = get_config(config_name)
    arena = get_arena(config.arena)
    ruleset = get_rule_set(config.ruleset)
    home = get_team_by_id(home_team_id, ruleset)
    away = get_team_by_id(away_team_id, ruleset)
    game_id = str(uuid.uuid1())
    game = Game(game_id, [home, away], arena, config, ruleset, home_team=home)
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


def save_game_exists(name):
    for save in host.get_saved_games():
        if save[1] == name.lower():
            return True
    return False


def save_game(game_id, name):
    name = name.replace("/", "").replace(".", "").lower()
    host.save_game(game_id, name)


def get_game(game_id):
    return host.get_game(game_id)


def load_game(name):
    return host.load_game(name)


def get_games():
    return host.get_games()


def get_saved_games():
    return host.get_saved_games()


def get_teams(ruleset):
    return get_all_teams(ruleset)


# Initialize with one game
new_game("a1", "b2")
