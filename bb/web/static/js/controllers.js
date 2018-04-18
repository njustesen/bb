
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
        var id = $routeParams.id;

        $scope.generateGameLog = function generateGameLog() {
            let text = "";
            for (let i in $scope.game.reports){
                if ($scope.game.reports[i].outcome_type in GameLogService.log_texts){
                    text += GameLogService.log_texts[$scope.game.reports[i].outcome_type] + "\n";
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

        $scope.square = function square(area, x, y) {
            let player = $scope.playerAt(area, x, y);
            if (player != null){
                //team = $scope.teamOfPlayer(player);
                //if (team.team_id == )
                $scope.selected_player = player;
            } else {
                $scope.selected_player = null;
            }
            console.log("Click on: " + area + ", x=" + x + ", y=" + y);
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
            let player_id = -1;
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
            if (player_id == -1){
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

        $scope.save = function save(game, shouldPublish) {
            if (game !== undefined 
                && game.title !== undefined && game.title != "") {

                var content = $('#textareaContent').val();
                if (content !== undefined && content != "") {
                    game.content = content;

                    if (shouldPublish != undefined && shouldPublish == true) {
                        game.is_published = true;
                    } else {
                        game.is_published = false;
                    }

                    // string comma separated to array
                    if (Object.prototype.toString.call(game.tags) !== '[object Array]') {
                        game.tags = game.tags.split(',');
                    }
                    
                    GameService.update(game).success(function(data) {
                        $location.path("/");
                    }).error(function(status, data) {
                        console.log(status);
                        console.log(data);
                    });
                }
            }
        };

        $scope.prettify = function prettify(text){
            let pretty = text.toLowerCase().split("_").join(" ");
            return pretty.charAt(0).toUpperCase() + pretty.slice(1);
        };

        $scope.act = function act(action){
            $scope.refreshing = true;
            GameService.act($scope.game.game_id, action).success(function(data) {
                $scope.game = data;
                $scope.gamelog = $scope.generateGameLog($scope.game);
                console.log(data);
                $scope.refreshing = false;
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
    }
]);