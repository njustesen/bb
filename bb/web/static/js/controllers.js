
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
        $('#textareaContent').wysihtml5({"font-styles": false});

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

appControllers.controller('GamePlayCtrl', ['$scope', '$routeParams', '$location', '$sce', 'GameService', 'IconService',
    function GamePlayCtrl($scope, $routeParams, $location, $sce, GameService, IconService) {
        $scope.game = {};
        $scope.loading = true;

        var id = $routeParams.id;

        GameService.get(id).success(function(data) {
            $scope.game = data;
            $scope.playersById = Object.assign({}, $scope.game.home_team.players_by_id, $scope.game.away_team.players_by_id);
            console.log(data);
            $scope.loading = false;
        }).error(function(status, data) {
            $location.path("/#/");
        });

        $scope.square = function square(area, x, y) {
            alert(area + ", x=" + x + ", y=" + y);
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
            let player = $scope.playersById[player_id];
            let team = $scope.teamOfPlayer[player.player_id];
            return {
                'player': player,
                'icon': $scope.iconName = IconService.playerIcons[team.race][player.position]
            };
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
        }
    }
]);