
appControllers.controller('GameListCtrl', ['$scope', 'GameService',
    function GameListCtrl($scope, GameService) {
        $scope.games = [];

        GameService.findAll().success(function(data) {
            $scope.games = data;
        });

        $scope.updatePublishState = function updatePublishState(game, shouldPublish) {
            if (game != undefined && shouldPublish != undefined) {

                GameService.changePublishState(game._id, shouldPublish).success(function(data) {
                    var games = $scope.games;
                    for (var gameKey in games) {
                        if (games[gameKey]._id == game._id) {
                            $scope.games[gameKey].is_published = shouldPublish;
                            break;
                        }
                    }
                }).error(function(status, data) {
                    console.log(status);
                    console.log(data);
                });
            }
        }


        $scope.deleteGame = function deletegame(id) {
            if (id != undefined) {

                GameService.delete(id).success(function(data) {
                    var games = $scope.games;
                    for (var gameKey in games) {
                        if (games[gameKey]._id == id) {
                            $scope.games.splice(gameKey, 1);
                            break;
                        }
                    }
                }).error(function(status, data) {
                    console.log(status);
                    console.log(data);
                });
            }
        }
    }
]);

appControllers.controller('GameCreateCtrl', ['$scope', '$location', 'GameService', 'TeamService',
    function GameCreateCtrl($scope, $location, GameService, TeamService) {

        TeamService.findAll().success(function(data) {
            $scope.teams = data;
            $scope.home_team_id = data[0].team_id;
            $scope.away_team_id = data[1].team_id;
        });

        $scope.home_player = "human"
        $scope.away_player = "human"

        $scope.save = function save(game, shouldPublish) {
            //var content = $('#textareaContent').val();
            game = {}
            game.home_team_id = $scope.home_team_id
            game.away_team_id = $scope.away_team_id
            game.home_player = $scope.home_player
            game.away_player = $scope.away_player

            GameService.create(game).success(function(data) {
                $location.path("/");
            }).error(function(status, data) {
                console.log(status);
                console.log(data);
            });
        }
    }
]);

appControllers.controller('GamePlayCtrl', ['$scope', '$routeParams', '$location', '$sce', 'GameService', 'IconService', 'GameLogService',
    function GamePlayCtrl($scope, $routeParams, $location, $sce, GameService, IconService, GameLogService) {
        $scope.game = {};
        $scope.loading = true;
        $scope.hover_player = null;
        $scope.selected_square = null;
        $scope.available_action_type = null;
        $scope.action_taker_home = null;
        $scope.action_taker_away = null;
        $scope.available_positions = [];
        $scope.local_state = {
            board: [],
            home_dugout: [],
            away_dugout: []
        };

        var id = $routeParams.id;

        $scope.generateGameLog = function generateGameLog() {
            let text = "";
            for (let i in $scope.game.reports){
                if ($scope.game.reports[i].outcome_type in GameLogService.log_texts){
                    let line = GameLogService.log_texts[$scope.game.reports[i].outcome_type] + "\n";
                    line = line.replace("<home_team>", $scope.game.home_team.name);
                    line = line.replace("<away_team>", $scope.game.away_team.name);
                    text += line;
                }
            }
            return text;
        }

        $scope.teamOfPlayer = function teamOfPlayer(player){
            if (player.player_id in $scope.game.home_team.players_by_id){
                return $scope.game.home_team;
            }
            if (player.player_id in $scope.game.away_team.players_by_id){
                return $scope.game.away_team;
            }
            return null;
        };

        $scope.playerIcon = function playerIcon(player, angled){
            let team = $scope.teamOfPlayer(player);
            let icon_base = IconService.playerIcons[team.race][player.position_name];
            let icon_num = "1";
            let team_letter = team.team_id == $scope.game.home_team.team_id ? "" : "b";
            let angle = "";
            let icon_name = icon_base + icon_num + team_letter + angle + ".gif";
            return icon_name;
        };

        $scope.newSquare = function newSquare(player_id, x, y, area, sub_area){
            let player = player_id != null ? $scope.playersById[player_id] : null;
            let player_state = player_id != null ? $scope.game.state.home_state.player_states[player_id] : null;
            let player_icon = player != null ? $scope.playerIcon(player, false) : null;
            return {
                x: x,
                y: y,
                player: player,
                player_state: player_state,
                player_icon: player_icon,
                selected: false,
                available_position: false,
                area: area,
                sub_area: sub_area
            };
        };

        $scope.setLocalState = function setLocalState(){
            for (let y = 0; y < $scope.game.state.field.board.length; y++){
                if ($scope.local_state.board.length <= y){
                    $scope.local_state.board.push([]);
                }
                for (let x = 0; x < $scope.game.state.field.board[y].length; x++){
                    let player_id = $scope.game.state.field.board[y][x];
                    let square = $scope.newSquare(player_id, x, y, 'field', '');
                    if ($scope.local_state.board[y].length <= x){
                        $scope.local_state.board[y].push(square);
                    } else {
                        $scope.local_state.board[y][x] = square;
                    }
                }
            }
            for (let y = 0; y < 15; y++){
                if ($scope.local_state.home_dugout.length <= y){
                    $scope.local_state.home_dugout.push([]);
                    $scope.local_state.away_dugout.push([]);
                }
                for (let x = 0; x < 2; x++){
                    let sub_area = '';
                    let home_player_id = null;
                    let home_square = null;
                    let away_player_id = null;
                    let away_square = null;
                    let idx = y*2+x;
                    if (y >= 11){
                        sub_area = 'casualties';
                        home_player_id = $scope.game.state.home_dugout.casualties[idx];
                        away_player_id = $scope.game.state.away_dugout.casualties[idx];
                    } else if (y >= 7){
                        sub_area = 'kod';
                        home_player_id = $scope.game.state.home_dugout.kod[idx];
                        away_player_id = $scope.game.state.away_dugout.kod[idx];
                    } else {
                        sub_area = 'reserves';
                        home_player_id = $scope.game.state.home_dugout.reserves[idx];
                        away_player_id = $scope.game.state.away_dugout.reserves[idx];
                    }
                    away_square = $scope.newSquare(away_player_id, x, y, 'dugout-away', sub_area);
                    home_square = $scope.newSquare(home_player_id, x, y, 'dugout-home', sub_area);
                    if ($scope.local_state.home_dugout[y].length <= x){
                        $scope.local_state.home_dugout[y].push(home_square);
                        $scope.local_state.away_dugout[y].push(away_square);
                    } else {
                        $scope.local_state.home_dugout[y][x] = home_square;
                        $scope.local_state.away_dugout[y][x] = away_square;
                    }
                }
            }
        };

        GameService.get(id).success(function(data) {
            $scope.game = data;
            $scope.playersById = Object.assign({}, $scope.game.home_team.players_by_id, $scope.game.away_team.players_by_id);
            $scope.gamelog = $scope.generateGameLog();
            $scope.setLocalState();
            console.log(data);
            $scope.loading = false;
        }).error(function(status, data) {
            $location.path("/#/");
        });

        $scope.select = function select(square){
            $scope.selected_square = square;
            if (square.area == 'field'){
                $scope.local_state.board[square.y][square.x].selected = true;
            } else if (square.area == 'dugout-home'){
                $scope.local_state.home_dugout[square.y][square.x].selected = true;
            } else if (square.area == 'dugout-away'){
                $scope.local_state.away_dugout[square.y][square.x].selected = true;
            }
        };

        $scope.resetSquares = function resetSquares(){
            $scope.selected_square = null;
            $scope.available_positions = [];
            for (let y = 0; y < $scope.local_state.board.length; y++){
                for (let x = 0; x < $scope.local_state.board[y].length; x++){
                    $scope.local_state.board[y][x].selected = false;
                    $scope.local_state.board[y][x].available_position = false;
                }
            }
            for (let y = 0; y < $scope.local_state.home_dugout.length; y++){
                for (let x = 0; x < $scope.local_state.home_dugout[y].length; x++){
                    $scope.local_state.home_dugout[y][x].selected = false;
                    $scope.local_state.home_dugout[y][x].available_position = false;
                }
            }
            for (let y = 0; y < $scope.local_state.away_dugout.length; y++){
                for (let x = 0; x < $scope.local_state.away_dugout[y].length; x++){
                    $scope.local_state.away_dugout[y][x].selected = false;
                    $scope.local_state.away_dugout[y][x].available_position = false;
                }
            }
        };

        $scope.setAvailablePositions = function setAvailablePositions(){
            for (let i in $scope.available_positions){
                let pos = $scope.available_positions[i];
                if (pos == null){
                    if ($scope.action_taker_home){
                        for (let y = 0; y < $scope.local_state.home_dugout.length; y++){
                            for (let x = 0; x < $scope.local_state.home_dugout[y].length; x++){
                                if (y <= 7 && $scope.local_state.home_dugout[y][x].player == null && $scope.selected_square.area == 'field'){
                                    $scope.local_state.home_dugout[y][x].available_position = true;
                                }
                            }
                        }
                    } else if ($scope.action_taker_away){
                        for (let y = 0; y < $scope.local_state.away_dugout.length; y++){
                            for (let x = 0; x < $scope.local_state.away_dugout[y].length; x++){
                                if (y <= 7 && $scope.local_state.away_dugout[y][x].player == null && $scope.selected_square.area == 'field'){
                                    $scope.local_state.away_dugout[y][x].available_position = true;
                                }
                            }
                        }
                    }
                } else {
                    $scope.local_state.board[pos.y][pos.x].available_position = true;
                }
            }
        };

        $scope.selectedPlayer = function selectedPlayer(){
            if ($scope.selected_square != null){
                return $scope.selected_square.player;
            }
            return null;
        };

        $scope.square = function square(square) {
            console.log("Click on: " + square);

            if (square.available_position && $scope.selected_square != null && $scope.selected_square.player != null){
                if (square.player != null && $scope.selected_square.player.player_id == square.player.player_id){
                    $scope.resetSquares();
                } else {
                    let action = {
                        'player_from_id': $scope.selectedPlayer() == null ? null : $scope.selectedPlayer().player_id,
                        'player_to_id': square.player == null ? null : square.player.player_id,
                        'pos_from': $scope.selected_square != null && $scope.selected_square.area == 'field' ? {'x': $scope.selected_square.x, 'y': $scope.selected_square.y} : null,
                        'pos_to': square.area == 'field' ? {'x': square.x, 'y': square.y} : null,
                        'team_home': null,
                        'idx': -1,
                        'action_type': $scope.available_action_type
                    };
                    $scope.act(action);
                }
            } else if (square.player == null){
                $scope.resetSquares();
            } else {
                $scope.resetSquares();
                $scope.select(square);
                for (let idx in $scope.game.available_actions){
                    let action = $scope.game.available_actions[idx];
                    if (action.positions.length > 0){
                        if (action.player_ids.length == 0 || (action.player_ids.indexOf($scope.selected_square.player.player_id) >= 0)){
                            $scope.available_positions = action.positions;
                            $scope.available_action_type = action.action_type;
                            $scope.action_taker_home = action.team;
                            $scope.action_taker_away = !action.team;
                        }
                    }
                }
                $scope.setAvailablePositions();
            }

        };

        $scope.squareHover = function squareHover(square) {
            if (square.player != null){
                $scope.hover_player = square.player;
            } else {
                $scope.hover_player = null;
            }
        };

        $scope.currentProc = function currentProc(){
            if ($scope.loading){
                return "";
            } else if ($scope.game.stack[$scope.game.stack.length-1] == "Pregame"){
                return "Pre-Game";
            } else if ($scope.game.stack[$scope.game.stack.length-1] == "WeatherTable"){
                return "Pre-Game";
            } else if ($scope.game.stack[$scope.game.stack.length-1] == "CoinToss"){
                return "Coin Toss";
            } else if ($scope.game.stack[$scope.game.stack.length-1] == "PostGame"){
                return "Post-Game";
            } else if ($scope.game.game_over){
                return "Game is Over";
            } else if ($scope.game.state.half == 1){
                return "1st half";
            } else if ($scope.game.state.half == 2){
                return "2nd half";
            }
        };

        $scope.playerInFocus = function playerInFocus(team) {
            let player = null;
            if ($scope.hover_player != null){
                player = $scope.hover_player;
                if (player != null && team.team_id == $scope.teamOfPlayer(player).team_id){
                    return player;
                }
            }
            if ($scope.selected_square != null && $scope.selected_square.player != null){
                if (team.team_id == $scope.teamOfPlayer($scope.selected_square.player).team_id){
                    return $scope.selected_square.player;
                }
            }
            return null;
        };

        $scope.prettify = function prettify(text){
            let pretty = text.toLowerCase().split("_").join(" ");
            return pretty.charAt(0).toUpperCase() + pretty.slice(1);
        };

        $scope.act = function act(action){
            console.log(action);
            $scope.refreshing = true;
            GameService.act($scope.game.game_id, action).success(function(data) {
                $scope.game = data;
                $scope.gamelog = $scope.generateGameLog($scope.game);
                console.log(data);
                $scope.setLocalState();
                $scope.refreshing = false;
                $scope.selected_square = null;
                $scope.available_positions = []
            }).error(function(status, data) {
                $location.path("/#/");
            });
        };

        $scope.pickActionType = function pickActionType(action){
            $scope.selected_action = undefined;
            if (action.positions.length == 0){
                $scope.act({'action_type': action.action_type, 'position': null});
            } else if (action.positions.length == 1){
                $scope.act({'action_type': action.action_type, 'position': action.positions[0]});
            } else {
                $scope.selected_action = action;
            }
        };

        $scope.showAction = function showAction(action) {
            // If no args -> show
            if (action.player_ids.length == 0 && action.positions.length == 0){
                return true;
            } else if (action.player_ids.length > 0 && $scope.selected_square != null && $scope.selected_square.player != null && action.player_ids.indexOf($scope.selected_square.player.player_id) >= 0 && action.positions.length == 0){
                return true;
            }
            return false;
        };
    }
]);