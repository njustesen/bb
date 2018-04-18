
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
        $scope.selected_player = null;
        $scope.selected_area = null;
        $scope.selected_square = null;
        $scope.available_positions = [];
        $scope.available_action_type = null;
        $scope.action_taker_home = null;
        $scope.action_taker_away = null;
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

        GameService.get(id).success(function(data) {
            $scope.game = data;
            $scope.playersById = Object.assign({}, $scope.game.home_team.players_by_id, $scope.game.away_team.players_by_id);
            $scope.gamelog = $scope.generateGameLog();
            console.log(data);
            $scope.loading = false;
        }).error(function(status, data) {
            $location.path("/#/");
        });

        $scope.is_selected_square = function is_selected_square(area, x, y){
            return $scope.selected_square != null && $scope.selected_area != null && $scope.selected_square.x == x && $scope.selected_square.y == y && $scope.selected_area == area;
        };

        $scope.is_available_position = function is_available_position(area, x, y){

            if (area == "dugout-home" && $scope.action_taker_home){
                if (y <= 7 && $scope.playerAt(area, x, y) == null && $scope.selected_area == "field"){
                    for (let idx in $scope.available_positions){
                        let position = $scope.available_positions[idx];
                        if (position == null){
                            return true;
                        }
                    }
                }
            }

            if (area == "dugout-away" && $scope.action_taker_away){
                if (y <= 7 && $scope.playerAt(area, x, y) == null && $scope.selected_area == "field"){
                    for (let idx in $scope.available_positions){
                        let position = $scope.available_positions[idx];
                        if (position == null){
                            return true;
                        }
                    }
                }
            }

            for (let idx in $scope.available_positions){
                let position = $scope.available_positions[idx];
                if (position != null && position.x == x && position.y == y){
                    return true;
                }
            }
            return false;
        };

        $scope.deselect = function deselect(){
            $scope.selected_player = null;
            $scope.selected_area = null;
            $scope.selected_square = null;
            $scope.available_positions = [];
        };

        $scope.square = function square(area, x, y) {
            console.log("Click on: " + area + ", x=" + x + ", y=" + y);
            let player = $scope.playerAt(area, x, y);

            if ($scope.is_available_position(area, x, y) && $scope.selected_player != null){
                if (player != null && $scope.selected_player.player_id == player.player_id){
                    $scope.deselect();
                }
                let action = {
                    'player_from_id': $scope.selected_player.player_id,
                    'player_to_id': player == null ? null : player.player_id,
                    'pos_from': $scope.selected_square != null && $scope.selected_area == 'field' ? $scope.selected_square : null,
                    'pos_to': area == 'field' ? {'x': x, 'y': y} : null,
                    'team_home': null,
                    'idx': -1,
                    'action_type': $scope.available_action_type
                };

                $scope.act(action);
                return;
            }

            if (player == null){
                // Deselect
                $scope.selected_square = null;
                $scope.selected_area = null;
            } else {
                $scope.selected_square = {'x':x, 'y':y};
                $scope.selected_area = area;
            }

            $scope.available_positions = [];
            if (player != null){
                $scope.selected_player = player;
                for (let idx in $scope.game.available_actions){
                    let action = $scope.game.available_actions[idx];
                    if (action.player_ids.length > 0 && action.player_ids.indexOf($scope.selected_player.player_id) >= 0){
                        $scope.available_positions = action.positions;
                        $scope.available_action_type = action.action_type;
                        $scope.action_taker_home = action.team;
                        $scope.action_taker_away = !action.team;
                    }
                }
            } else {
                $scope.deselect();
            }
        };

        $scope.squareHover = function squareHover(area, x, y) {
            let player = $scope.playerAt(area, x, y);
            if (player != null){
                $scope.hover_player = player;
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

        $scope.teamOfPlayer = function teamOfPlayer(player){
            if (player.player_id in $scope.game.home_team.players_by_id){
                return $scope.game.home_team;
            }
            if (player.player_id in $scope.game.away_team.players_by_id){
                return $scope.game.away_team;
            }
            return null;
        };

        $scope.playerAt = function playerAt(area, x, y){
            let player_id = null;
            if (area == "field"){
                player_id = $scope.game.state.field.board[y][x];
            }
            let dugout = undefined;
            if (area == "dugout-home"){
                dugout = $scope.game.state.home_dugout;
            } else if (area == "dugout-away"){
                dugout = $scope.game.state.away_dugout;
            }
            if (dugout != undefined){
                let idx = y*2+x;
                if (idx <= 14){
                    if (idx < dugout.reserves.length){
                        player_id = dugout.reserves[idx];
                    }
                } else if (idx <= 20){
                    if (idx < dugout.kod.length){
                        player_id = dugout.kod[idx];
                    }
                } else if (idx <= 24){
                    if (idx < dugout.casualties.length){
                        player_id = dugout.casualties[idx];
                    }
                }
            }
            if (player_id == null){
                return null;
            }
            return $scope.playersById[player_id];
        };

        $scope.playerIcon = function playerIcon(player, angled){
            let team = $scope.teamOfPlayer(player);
            let icon_base = IconService.playerIcons[team.race][player.position_name];
            let icon_num = "1";
            let team_letter = team.team_id == $scope.game.home_team.team_id ? "" : "b";
            let angle = "";
            //if (angled && $scope.selected_player != null && $scope.selected_player.player_id == player.player_id){
            //    angle = "an";
            //}
            let icon_name = icon_base + icon_num + team_letter + angle + ".gif";
            return icon_name;
        };

        $scope.playerInFocus = function playerInFocus(team) {
            let player = null;
            if ($scope.hover_player != null){
                player = $scope.hover_player;
                if (player != null && team.team_id == $scope.teamOfPlayer(player).team_id){
                    return player;
                }
            }
            if ($scope.selected_player != null){
                player = $scope.selected_player;
                if (player != null && team.team_id == $scope.teamOfPlayer(player).team_id){
                    return player;
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
                $scope.refreshing = false;
                $scope.selected_square = null;
                $scope.selected_player = null;
                $scope.selected_area = null;
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
            } else if (action.player_ids.length > 0 && $scope.selected_player != null && action.player_ids.indexOf($scope.selected_player.player_id) >= 0 && action.positions.length == 0){
                return true;
            }
            return false;
        };
    }
]);