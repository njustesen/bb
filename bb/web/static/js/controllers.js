
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

appControllers.controller('GamePlayCtrl', ['$scope', '$routeParams', '$location', '$sce', 'GameService',
    function GamePlayCtrl($scope, $routeParams, $location, $sce, GameService) {
        $scope.game = {};
        var id = $routeParams.id;

        GameService.get(id).success(function(data) {
            $scope.game = data;
            $('#textareaContent').wysihtml5({"font-styles": false});
            $('#textareaContent').val($sce.trustAsHtml(data.content));
        }).error(function(status, data) {
            $location.path("/#/");
        });

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
