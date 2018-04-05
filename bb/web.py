from flask import Flask, request
from bb import api
from bb.util import *
from bb.model import Action, Square
from bb.table import ActionType
import json
app = Flask(__name__)

'''
To start server:
$ export FLASK_DEBUG=1
$ flask run
'''

@app.route('/', methods=['GET'])
def home():
    return 'Hello, World!'


@app.route('/game/create', methods=['POST'])
def new_game():
    game = api.new_game()
    return json.dumps(game)


@app.route('/game/<int:game_id>/step', methods=['POST'])
def step(game_id):
    action_type_name = request.args.get('action')
    action_type = parse_enum(ActionType, action_type_name)
    from_x = request.args.get('from_x')
    from_y = request.args.get('from_x')
    pos_from = None if from_x is None or from_y is None else Square(from_x, from_y)
    to_x = request.args.get('to_x')
    to_y = request.args.get('to_y')
    pos_to = None if to_x is None or to_y is None else Square(to_x, to_y)
    player_from_id = request.args.get('player_from_id')
    player_to_id = request.args.get('player_to_id')
    idx = request.args.get('idx')
    team_home = request.args.get('team_home')
    action = Action(action_type, pos_from, pos_to, player_from_id, player_to_id, idx, team_home)
    game = api.step(game_id, action)
    return json.dumps(game)


@app.route('/game/<int:game_id>/', methods=['GET'])
def get_game(game_id):
    return api.get_game(game_id)
