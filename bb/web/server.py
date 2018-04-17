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


@app.route('/games/', methods=['GET'])
def get_all_games():
    games = api.get_games()
    game_list = []
    for game in games:
        game_list.append(game.to_simple())
    return json.dumps(game_list)


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
    square = request.args.get(action['position'])
    action = Action(action_type, pos_from=square)
    game = api.step(game_id, action)
    return json.dumps(game.to_simple())


@app.route('/games/<game_id>', methods=['GET'])
def get_game(game_id):
    return json.dumps(api.get_game(game_id).to_simple())


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
