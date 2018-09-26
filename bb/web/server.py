from flask import Flask, request, render_template, Response
from bb.core.util import *
from bb.core import api
from bb.core.model import Action, Square
from bb.core.table import ActionType
from bb.web.backend.users import *
import json
app = Flask(__name__)

'''
To start server:
$ export FLASK_DEBUG=1
$ flask run
'''

user_store = UserStore()


@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')


@app.route('/game/create', methods=['PUT'])
def create():
    data = json.loads(request.data)
    game = api.new_game(data['game']['home_team_id'], data['game']['away_team_id'])
    return json.dumps(game.to_simple())

@app.route('/game/save', methods=['POST'])
def save():
    game_id = json.loads(request.data)['game_id']
    name = json.loads(request.data)['name']
    if len(name) > 2 and len(name) < 40 and not api.save_game_exists(name):
        api.save_game(game_id, name)
        return json.dumps("Game was successfully saved")
    else:
        raise Exception("Cannot save this game")

'''
@app.route('/games/', methods=['GET'])
def get_games():
    games = api.get_games()
    game_list = []
    for game in games:
        game_list.append(game.to_simple())
    return json.dumps(game_list)
'''

@app.route('/games/', methods=['GET'])
def get_all_games():
    games = api.get_games()
    saved_games = api.get_saved_games()
    game_list = [game.to_simple() for game in games]
    saved_game_list = [{'game': save[0].to_simple(), 'name': save[1]} for save in saved_games]
    return json.dumps({
        'games': game_list,
        'saved_games': saved_game_list
    })

@app.route('/teams/', methods=['GET'])
def get_all_teams():
    teams = api.get_teams()
    team_list = []
    for team in teams:
        team_list.append(team.to_simple())
    return json.dumps(team_list)


@app.route('/games/<game_id>/act', methods=['POST'])
def step(game_id):
    action = json.loads(request.data)['action']
    action_type = parse_enum(ActionType, action['action_type'])
    pos_from = Square(action['pos_from']['x'], action['pos_from']['y']) if 'pos_from' in action and action['pos_from'] is not None else None
    pos_to = Square(action['pos_to']['x'], action['pos_to']['y']) if 'pos_to' in action and action['pos_to'] is not None else None
    player_from_id = action['player_from_id'] if 'player_from_id' in action else None
    player_to_id = action['player_to_id'] if 'player_to_id' in action else None
    idx = action['idx'] if 'idx' in action else -1
    team_home = action['team_home'] if 'team_home' in action else None
    action = Action(action_type, pos_from=pos_from, pos_to=pos_to, player_from_id=player_from_id, player_to_id=player_to_id, idx=idx, team_home=team_home)
    game = api.step(game_id, action)
    return json.dumps(game.to_simple())


@app.route('/games/<game_id>', methods=['GET'])
def get_game(game_id):
    return json.dumps(api.get_game(game_id).to_simple())


@app.route('/game/load/<name>', methods=['GET'])
def load_game(name):
    return json.dumps(api.load_game(name).to_simple())


if __name__ == '__main__':
    # Change jinja notation to work with angularjs
    jinja_options = app.jinja_options.copy()
    jinja_options.update(dict(
        block_start_string='<%',
        block_end_string='%>',
        variable_start_string='%%',
        variable_end_string='%%',
        comment_start_string='<#',
        comment_end_string='#>'
    ))
    app.jinja_options = jinja_options

    app.config['TEMPLATES_AUTO_RELOAD']=True
    app.run(debug=True,use_reloader=True)
