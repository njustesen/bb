
appControllers.controller('GameListCtrl', ['$scope', '$window', 'GameService',
    function GameListCtrl($scope, $window, GameService) {
        $scope.games = [];
        $scope.savedGames = [];

        GameService.findAll().success(function(data) {
            $scope.games = data.games;
            $scope.savedGames = data.saved_games;
        });

        $scope.loadGame = function loadGame(name){
            GameService.load(name).success(function(data) {
                 $window.location.href = '/#/game/play/' + data.game_id
            }).error(function(status, data) {
                console.log(status);
                console.log(data);
            });
        };

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
        };
    }
]);

appControllers.controller('GameCreateCtrl', ['$scope', '$location', 'GameService', 'TeamService', 'IconService',
    function GameCreateCtrl($scope, $location, GameService, TeamService, IconService) {

        $scope.teams = [];
        $scope.home_team_id = null;
        $scope.away_team_id = null;

        TeamService.findAll().success(function(data) {
            $scope.teams = data;
        });

        $scope.prettify = function prettify(text){
            let pretty = text.toLowerCase().split("_").join(" ");
            return pretty.charAt(0).toUpperCase() + pretty.slice(1);
        };

        $scope.getTeam = function getTeam(team_id){
            for (let i in $scope.teams){
                if ($scope.teams[i].team_id == team_id){
                    return $scope.teams[i];
                }
            }
            return null;
        };

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
        };
    }
]);

appControllers.controller('GamePlayCtrl', ['$scope', '$routeParams', '$location', '$sce', 'GameService', 'IconService', 'GameLogService',
    function GamePlayCtrl($scope, $routeParams, $location, $sce, GameService, IconService, GameLogService) {
        $scope.game = {};
        $scope.saved = false;
        $scope.loading = true;
        $scope.refreshing = false;
        $scope.hover_player = null;
        $scope.selected_square = null;
        $scope.selected_player = null;
        $scope.main_action = null;
        $scope.available_positions = [];
        $scope.modalVisible = false;
        $scope.modelError = false;
        $scope.passOptions = false;
        $scope.local_state = {
            ball_position: null,
            ball_in_air: null,
            board: [],
            home_dugout: [],
            away_dugout: [],
            player_positions: {}
        };

        $scope.getAvailable = function getAvailable(square){
            if (square.special_action_type === "PASS" && $scope.passOptions) {
                return square.special_available;
            } else {
                return square.available;
            }
        };

        $scope.getAgiRolls = function getAgiRolls(square){
            if (square.special_action_type === "PASS" && $scope.passOptions) {
                return square.special_agi_rolls;
            } else {
                return square.agi_rolls;
            }
        };

        $scope.getActionType = function getActionType(square){
            if (square.special_action_type === "PASS" && $scope.passOptions) {
                return square.special_action_type;
            } else {
                return square.action_type;
            }
        };

        document.addEventListener('keydown', function(event) {
            if (event.ctrlKey){
                $scope.passOptions = !$scope.passOptions;
                $scope.$apply();
            }
        });

        $scope.saveGame = function saveGame(name){
            $scope.modelError = false;
            // Get state
            GameService.save($scope.game.game_id, name).success(function(data) {
                $scope.saved = true;
                $scope.modalVisible = false;
            }).error(function(status, data) {
                $scope.modelError = true;
                //$location.path("/#/");
            });
        };

        var id = $routeParams.id;

        $scope.showReport = function showReport(report){
            return report.outcome_type in GameLogService.log_texts;
        };

        $scope.getPlayer = function getPlayer(player_id){
            if (player_id in $scope.game.home_team.players_by_id){
                return $scope.game.home_team.players_by_id[player_id];
            }
            if (player_id in $scope.game.away_team.players_by_id){
                return $scope.game.away_team.players_by_id[player_id];
            }
            return null;
        };

        $scope.title = function(str){
            return str.replace(
                /\w\S*/g,
                function(txt) {
                    return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
                }
            );
        };

        $scope.reportBlock = function reportBlock(report) {
            if ($scope.showReport(report)){
                let line = GameLogService.log_texts[report.outcome_type] + "\n";
                line = line.replace("<home_team>", "<span class='label label-danger'>" + $scope.game.home_team.name + "</span> ");
                line = line.replace("<away_team>", "<span class='label label-primary'>" + $scope.game.away_team.name + "</span> ");
                line = line.replace("<team>", "<span class='label label-" + (report.team_home ? ("danger'>" + $scope.game.home_team.name) : ("primary'>" + $scope.game.away_team.name)) + "</span> " );
                if (report.skill !== null){
                    line = line.replace("<skill>", '<span class="label label-success skill">' + $scope.title(report.skill) + '</span>');
                }
                let n = report.n;
                if (typeof(n) === "string"){
                    n = report.n.replace("NONE", "badly hurt").toLowerCase();
                }
                line = line.replace("<n>", n);
                if (report.player_id != null){
                    let player = $scope.getPlayer(report.player_id);
                    let team = $scope.teamOfPlayer(player);
                    line = line.replace("<player>", "<span class='label label-" + (team.team_id === $scope.game.home_team.team_id ? ("danger'>" + player.nr + ". " + player.name) : ("primary'>" + player.nr + ". " + player.name)) + "</span> " );
                    line = line.replace("<players>", "<span class='label label-" + (team.team_id === $scope.game.home_team.team_id ? ("danger'>" + player.nr + ". " + player.name) : ("primary'>" + player.nr + ". " + player.name + "'s")) + "</span> " );
                }
                return line;
            }
            return null;
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

        $scope.playerIcon = function playerIcon(player){
            let team = $scope.teamOfPlayer(player);
            let icon_base = IconService.playerIcons[team.race][player.position_name];
            let icon_num = "1";
            let team_letter = team.team_id == $scope.game.home_team.team_id ? "" : "b";
            let angle = player.player_id === $scope.game.state.active_player_id ? "an" : "";
            let icon_name = icon_base + icon_num + team_letter + angle + ".gif";
            return icon_name;
        };

        $scope.getCursor = function getCursor(square){
            if (square.available && square.action_type === "HANDOFF"){
                return "cursor: url(static/img/icons/actions/handover.gif), auto";
            } else if (square.available && square.action_type === "BLOCK"){
                return "cursor: url(static/img/icons/actions/block.gif), auto";
            } else if (square.available && square.action_type === "FOUL"){
                return "cursor: url(static/img/icons/actions/foul.gif), auto";
            } else if (square.available && square.action_type === "PASS"){
                return "cursor: url(static/img/icons/actions/pass.gif), auto";
            }
            return "";
        };

        $scope.clickAction = function clickAction(event, action){
            event.stopPropagation();
            for (let idx in $scope.game.available_actions) {
                let a = $scope.game.available_actions[idx];
                if (a.action_type === "START_MOVE" && action === "move"){
                    $scope.pickActionType(a);
                } else if (a.action_type === "START_BLOCK" && action === "block"){
                    $scope.pickActionType(a);
                } else if (a.action_type === "START_PASS" && action === "pass"){
                    $scope.pickActionType(a);
                } else if (a.action_type === "START_HANDOFF" && action === "handoff"){
                    $scope.pickActionType(a);
                } else if (a.action_type === "START_BLITZ" && action === "blitz"){
                    $scope.pickActionType(a);
                } else if (a.action_type === "START_FOUL" && action === "foul"){
                    $scope.pickActionType(a);
                }
            }
        };

        $scope.playerStartAction = function playerStartAction(x, y, typeName){
            if ($scope.selected_square == null || $scope.selectedPlayer().player_id == null || $scope.selected_square.x !== x || $scope.selected_square.y !== y){
                return false;
            }
            for (let idx in $scope.game.available_actions){
                let action = $scope.game.available_actions[idx];
                if (action.player_ids.indexOf($scope.selectedPlayer().player_id) === -1) {
                    continue;
                }
                if (action.action_type.indexOf("START_") >= 0 && action.action_type.split("START_")[1].toLowerCase() === typeName){
                    return true;
                }
            }
            return false;
        };

        $scope.newSquare = function newSquare(player_id, x, y, area, sub_area, number){
            let player = null;
            let player_state = null;
            let player_icon = null;
            if (player_id != null){
                player = $scope.playersById[player_id];
                let team = $scope.teamOfPlayer(player);
                player_state = null;
                if (team.team_id === $scope.game.home_team.team_id){
                    player_state = $scope.game.state.home_state.player_states[player_id];
                } else {
                    player_state = $scope.game.state.away_state.player_states[player_id];
                }
                player_icon = player != null ? $scope.playerIcon(player) : null;
            }
            let ball = $scope.game.state.field.ball_position != null ? ($scope.game.state.field.ball_position.x === x && $scope.game.state.field.ball_position.y === y) : null;
            return {
                x: x,
                y: y,
                player: player,
                player_state: player_state,
                player_icon: player_icon,
                selected: false,
                available: false,
                special_available: false,
                action_type: undefined,
                special_action_type: undefined,
                agi_roll: 0,
                special_agi_roll: 0,
                roll: false,
                block_roll: 0,
                area: area,
                sub_area: sub_area,
                ball: ball,
                num: number
            };
        };

        $scope.clearSquareAction = function clearSquare(square) {
            square.available = false;
            square.agi_roll = 0;
            square.block_roll = 0;
            square.action_type = undefined;
        };

        $scope.setAvailablePositions = function setAvailablePositions(){
            $scope.available_select_positions = [];
            $scope.available_move_positions = [];
            $scope.available_block_positions = [];
            $scope.available_handoff_positions = [];
            $scope.available_pass_positions = [];
            $scope.available_foul_positions = [];
            $scope.available_dodge_rolls = [];
            $scope.available_block_rolls = [];
            $scope.available_block_agi_rolls = [];
            $scope.available_handoff_rolls = [];
            $scope.available_pass_rolls = [];
            $scope.available_players = [];
            $scope.available_interception_players = [];
            $scope.available_interception_rolls = [];
            $scope.available_special_pass_actions = [];
            $scope.available_special_rolls = [];
            $scope.main_action = null;
            for (let idx in $scope.game.available_actions){
                let action = $scope.game.available_actions[idx];
                if (action.positions.length > 0){
                    // If an available player is selected
                    $scope.main_action = action;
                    if (action.player_ids.length === 0 || ($scope.selectedPlayer() != null && action.player_ids.indexOf($scope.selectedPlayer().player_id) >= 0) || action.player_ids.length === 1){
                        if (action.action_type === "BLOCK") {
                            $scope.available_block_positions = action.positions;
                            $scope.available_block_rolls = action.block_rolls;
                            $scope.available_block_agi_rolls = action.agi_rolls;
                        } else if (action.action_type === "PASS"){
                            $scope.available_pass_positions = action.positions;
                            $scope.available_pass_rolls = action.agi_rolls;
                        } else if (action.action_type === "HANDOFF"){
                            $scope.available_handoff_positions = action.positions;
                        } else if (action.action_type === "FOUL"){
                            $scope.available_foul_positions = action.positions;
                        } else if (action.action_type === "MOVE"){
                            $scope.available_move_positions = action.positions;
                            $scope.available_dodge_rolls = action.agi_rolls;
                        } else {
                            $scope.available_select_positions = action.positions;
                        }
                    }
                }
                if (action.action_type === "INTERCEPTION") {
                    $scope.available_interception_players = action.player_ids;
                    $scope.available_interception_rolls = action.agi_rolls;
                    $scope.main_action = action;
                } else {
                    // Add available players
                    if (action.player_ids.length > 0){
                        if (!(action.action_type.startsWith("END_") || action.action_type.startsWith("START_"))) {
                            $scope.main_action = action;
                        }
                        if ($scope.available_players.length !== 1){
                            for (let p in action.player_ids){
                                $scope.available_players.push(action.player_ids[p]);
                            }
                        }
                    }
                    // Add player positions to available positions if none is selected
                    if ($scope.available_players.length > 1 && $scope.selectedPlayer() == null){
                        for (let p in action.player_ids){
                            $scope.available_select_positions.push($scope.local_state.player_positions[action.player_ids[p]]);
                        }
                    }
                }
            }
            // Select squares
            for (let i in $scope.available_select_positions){
                let pos = $scope.available_select_positions[i];
                // Reserves positions
                if (pos == null && $scope.selected_square != null && $scope.selected_square.area === 'field'){
                    if ($scope.main_action.team === true){
                        for (let y = 0; y < $scope.local_state.home_dugout.length; y++){
                            for (let x = 0; x < $scope.local_state.home_dugout[y].length; x++){
                                if (y <= 7 && $scope.local_state.home_dugout[y][x].player == null){
                                    $scope.local_state.home_dugout[y][x].available = true;
                                    $scope.local_state.home_dugout[y][x].action_type = $scope.main_action.action_type;
                                }
                            }
                        }
                    } else if ($scope.main_action.team === false){
                        for (let y = 0; y < $scope.local_state.away_dugout.length; y++){
                            for (let x = 0; x < $scope.local_state.away_dugout[y].length; x++){
                                if (y <= 7 && $scope.local_state.away_dugout[y][x].player == null){
                                    $scope.local_state.away_dugout[y][x].available = true;
                                    $scope.local_state.home_dugout[y][x].action_type = $scope.main_action.action_type;
                                }
                            }
                        }
                    }
                    // Field positions
                } else if (pos != null) {
                    $scope.local_state.board[pos.y][pos.x].available = true;
                    if ($scope.main_action !== null) {
                        $scope.local_state.board[pos.y][pos.x].action_type = $scope.main_action.action_type;
                    }
                }
                // Crowd in dugouts - available during pushes
                if (pos != null){
                    if (pos.x === 0 && pos.y > 0 && pos.y < $scope.local_state.board.length - 1){
                        $scope.local_state.home_dugout[pos.y-1][1].available = true;
                    }
                    if (pos.x === $scope.local_state.board[0].length - 1 && pos.y > 0 && pos.y < $scope.local_state.board.length - 1){
                        $scope.local_state.away_dugout[pos.y-1][0].available = true;
                    }
                }
            }

            // Select player if only one available
            if ($scope.available_players.length === 1){
                $scope.select($scope.local_state.player_positions[$scope.available_players[0]])
            }

            // Pass squares
            for (let i in $scope.available_pass_positions) {
                let pos = $scope.available_pass_positions[i];
                let player = $scope.local_state.board[pos.y][pos.x].player;
                if (player !== null){
                    let team = $scope.teamOfPlayer(player);
                    let player_state = $scope.playerState(player);
                    if ((team === $scope.game.home_team) === $scope.local_state.team_turn &&
                            player_state !== "DOWN" && player_state !== "STUNNED" && player_state !== "DOWN_USED") {
                        $scope.local_state.board[pos.y][pos.x].available = true;
                        $scope.local_state.board[pos.y][pos.x].action_type = "PASS";
                        if ($scope.available_pass_rolls.length > i) {
                            $scope.local_state.board[pos.y][pos.x].agi_rolls = $scope.available_pass_rolls[i];
                        }
                    }
                }
                $scope.local_state.board[pos.y][pos.x].special_available = true;
                $scope.local_state.board[pos.y][pos.x].special_action_type = "PASS";
                if ($scope.available_pass_rolls.length > i) {
                    $scope.local_state.board[pos.y][pos.x].special_agi_rolls = $scope.available_pass_rolls[i];
                }
            }

            // Interception squares
            for (let i in $scope.available_interception_players){
                let player_id = $scope.available_interception_players[i];
                let pos = $scope.local_state.player_positions[player_id];
                pos.available = true;
                pos.action_type = "INTERCEPTION";
                if ($scope.available_interception_rolls.length > i){
                    pos.agi_rolls = $scope.available_interception_rolls[i];
                }
            }

            // Move squares
            for (let i in $scope.available_move_positions) {
                let pos = $scope.available_move_positions[i];
                $scope.local_state.board[pos.y][pos.x].available = true;
                $scope.local_state.board[pos.y][pos.x].action_type = "MOVE";
                if ($scope.available_dodge_rolls.length > i){
                    $scope.local_state.board[pos.y][pos.x].agi_rolls = $scope.available_dodge_rolls[i];
                }
            }

            // Block squares
            for (let i in $scope.available_block_positions) {
                let pos = $scope.available_block_positions[i];
                $scope.local_state.board[pos.y][pos.x].available = true;
                $scope.local_state.board[pos.y][pos.x].action_type = "BLOCK";
                if ($scope.available_block_rolls.length > i){
                    $scope.local_state.board[pos.y][pos.x].block_roll = $scope.available_block_rolls[i];
                }
                if ($scope.available_block_agi_rolls.length > i){
                    $scope.local_state.board[pos.y][pos.x].agi_rolls = $scope.available_block_agi_rolls[i];
                }
            }

            // Foul squares
            for (let i in $scope.available_foul_positions) {
                let pos = $scope.available_foul_positions[i];
                $scope.local_state.board[pos.y][pos.x].available = true;
                $scope.local_state.board[pos.y][pos.x].action_type = "FOUL";
                $scope.local_state.board[pos.y][pos.x].available_foul_position = true;
            }

            // Hand-off squares
            for (let i in $scope.available_handoff_positions) {
                let pos = $scope.available_handoff_positions[i];
                $scope.local_state.board[pos.y][pos.x].available = true;
                $scope.local_state.board[pos.y][pos.x].action_type = "HANDOFF";
                if ($scope.available_dodge_rolls.length > i){
                    $scope.local_state.board[pos.y][pos.x].agi_rolls = $scope.available_handoff_rolls[i];
                }
            }
        };

        $scope.getTile = function(x, y){
            let tile = $scope.game.arena.board[y][x];
            if (tile === "CROWD"){
                return "crowd";
            }
            return "field";
        };

        $scope.setLocalState = function setLocalState(){
            $scope.local_state.player_positions = {};
            $scope.local_state.ball_in_air = $scope.game.state.ball_in_air;
            $scope.local_state.ball_position = $scope.game.state.ball_position;
            $scope.local_state.team_turn = $scope.game.state.team_turn;
            for (let y = 0; y < $scope.game.state.field.board.length; y++){
                if ($scope.local_state.board.length <= y){
                    $scope.local_state.board.push([]);
                }
                for (let x = 0; x < $scope.game.state.field.board[y].length; x++){
                    let player_id = $scope.game.state.field.board[y][x];
                    let square = $scope.newSquare(player_id, x, y, $scope.getTile(x, y), '', undefined);
                    if (player_id != null){
                        $scope.local_state.player_positions[player_id] = square;
                    }
                    if ($scope.selected_square != null && $scope.selected_square.player != null && $scope.selected_square.player.player_id === player_id){
                        $scope.selected_square = square;
                    }
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
                    if (y >= 12){
                        sub_area = 'casualties';
                        home_player_id = $scope.game.state.home_dugout.casualties[idx-12*2];
                        away_player_id = $scope.game.state.away_dugout.casualties[idx-12*2];
                    } else if (y >= 8){
                        sub_area = 'kod';
                        home_player_id = $scope.game.state.home_dugout.kod[idx-8*2];
                        away_player_id = $scope.game.state.away_dugout.kod[idx-8*2];
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
            for (let i = 0; i < $scope.game.squares_moved.length; i++){
                $scope.local_state.board[$scope.game.squares_moved[i].y][$scope.game.squares_moved[i].x].number = i
            }
        };

        $scope.newAction = function newAction(action_type){
            return {
                'player_from_id': null,
                'player_to_id': null,
                'pos_from': null,
                'pos_to': null,
                'team_home': null,
                'idx': -1,
                'action_type': action_type
            };
        };

        $scope.checkForReload =  function checkForReload(time){
            if ($scope.available_positions.length == 0){
                setTimeout(function(){
                    if (!$scope.loading && !$scope.refreshing && $scope.game.available_actions.length == 0){
                        $scope.act($scope.newAction('CONTINUE'));
                    }
                }, time);
            }
        };

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

        $scope.resetSquares = function resetSquares(deselect){
            if (deselect){
                $scope.selected_square = null;
            }
            $scope.available_positions = [];
            for (let y = 0; y < $scope.local_state.board.length; y++){
                for (let x = 0; x < $scope.local_state.board[y].length; x++){
                    $scope.local_state.board[y][x].selected = false;
                    $scope.local_state.board[y][x].available_position = false;
                    $scope.local_state.board[y][x].roll = false;
                    $scope.local_state.board[y][x].block_roll = 0;
                    $scope.local_state.board[y][x].agi_rolls = [];
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

        $scope.selectedPlayer = function selectedPlayer(){
            if ($scope.selected_square != null){
                return $scope.selected_square.player;
            }
            return null;
        };

        $scope.playerState = function playerReadyState(player){
            let state = undefined;
            if ($scope.teamOfPlayer(player) === $scope.game.home_team){
                return $scope.game.state.home_state.player_states[player.player_id];
            } else {
                return $scope.game.state.away_state.player_states[player.player_id];
            }
        };

        $scope.playerReadyState = function playerReadyState(player){
            let state = undefined;
            if ($scope.teamOfPlayer(player) === $scope.game.home_team){
                state = $scope.game.state.home_state.player_states[player.player_id].player_ready_state;
                if (state === "MNG"){
                    state = $scope.game.state.home_state.injures[player.player_id];
                }
            } else {
                state = $scope.game.state.away_state.player_states[player.player_id].player_ready_state;
                if (state === "MNG"){
                    state = $scope.game.state.away_state.injures[player.player_id];
                }
            }
            return state.replace("_READY", "").replace("_", " ");
        };

        $scope.playerReadyStateClass = function playerStateClass(player){
            let state = $scope.playerState(player);
            if (state == "READY" || state == "DOWN"){
                return "success";
            } if (state == "STUNNED"){
                return "warning";
            } else if (state == "USED" || state == "DOWN USED" || state == "STUNNED" || state == "HEATED" || state == "BONE HEADED" || state == "HYPNOTIZED" || state == "REALLY STUPID" || state == "REALLY STUPID"){
                return "secondary";
            } else if (state == "KOD"){
                return "warning";
            } else if (state == "BH" || state == "MNG" || state == "DEAD" || state == ""){
                return "danger";
            }
            return "light";
        };

        $scope.placeBall = function placeBall(square){
            // Remove ball first
            for (let y = 0; y < $scope.local_state.board.length; y++){
                for (let x = 0; x < $scope.local_state.board[y].length; x++){
                    $scope.local_state.board[y][x].ball = false;
                }
            }
            // Place ball
            $scope.local_state.board[square.y][square.x].ball = true;
            $scope.local_state.ball_in_air = true;
            $scope.local_state.ball_position = square;
        };

        $scope.create_action = function create_action(square){
            return {
                'player_from_id': $scope.selectedPlayer() == null ? null : $scope.selectedPlayer().player_id,
                'player_to_id': square.player == null ? null : square.player.player_id,
                'pos_from': $scope.selected_square != null && $scope.selected_square.area === 'field' ? {'x': $scope.selected_square.x, 'y': $scope.selected_square.y} : null,
                'pos_to': square.area === 'field' ? {'x': square.x, 'y': square.y} : null,
                'team_home': null,
                'idx': -1,
                'action_type': $scope.getActionType(square)
            };
        };

        $scope.square = function square(square) {
            console.log("Click on: " + square);

            if (square === undefined){
                return;
            }

            // If position is available
            if ($scope.main_action != null && $scope.getAvailable(square)){

                // Hot-fix for interceptions
                if ($scope.main_action.action_type === 'INTERCEPTION' || $scope.main_action.action_type === "SELECT_PLAYER"){
                    $scope.selected_square = square;
                }

                // If action does not require a selected player or a player is selected
                if ($scope.main_action.player_ids.length === 0 || ($scope.selectedPlayer() != null)){

                    // If player is selected or only one player available
                    if ($scope.available_players.length <= 1 || $scope.selectedPlayer() != null){

                        // Convert dugout squares to field (crowd) squares if push procedure
                        let crowd = $scope.game.stack[$scope.game.stack.length-1] === "Push" && square.area.startsWith("dugout");
                        let crowd_square = {
                            y: square.y+1,
                            area: 'field'
                        };
                        if (crowd){
                            if (square.area === "dugout-home"){
                                crowd_square.x = 0;
                            } else if (square.area === "dugout-away"){
                                crowd_square.x = $scope.local_state.board[0].length-1;
                            }
                        }
                        // Otherwise - send action
                        let action = null;
                        if (crowd){
                            action = $scope.create_action(crowd_square);
                        } else {
                            action = $scope.create_action(square);
                        }
                        $scope.act(action);
                    } else if (square.player != null && $scope.selectedPlayer() != null && $scope.selectedPlayer().player_id === square.player.player_id){
                        // Only deselect if other players are available
                        if ($scope.available_players.length !== 1) {
                            $scope.resetSquares(true);
                            $scope.setAvailablePositions();
                        }
                        return;
                    } else if ($scope.main_action.action_type === "PLACE_BALL"){
                        $scope.placeBall(square);
                        $scope.resetSquares(true);
                        $scope.setAvailablePositions();
                    }
                }
            }
            if (square.player == null){
                // Clicked on an empty square with no selected player
                if ($scope.available_players.length !== 1) {
                    $scope.resetSquares(true);
                }
                $scope.setAvailablePositions();
            } else {
                // Clicked on a player - select it - unless only non-player actions
                if ($scope.main_action == null || $scope.main_action.action_type !== "PLACE_BALL"){
                    if ($scope.available_players.length !== 1){
                        $scope.resetSquares(true);
                        $scope.select(square);
                    }
                    $scope.setAvailablePositions();
                }
            }

        };

        $scope.squareHover = function squareHover(square) {
            if (square.player != null){
                $scope.hover_player = square.player;
            } else {
                $scope.hover_player = null;
            }
        };

        $scope.currentProc = function currentProc(team){
            if ($scope.loading){
                return "";
            } else if ($scope.game.stack[$scope.game.stack.length-1] == "Pregame" && team == null){
                return "Pre-Game";
            } else if ($scope.game.stack[$scope.game.stack.length-1] == "WeatherTable" && team == null){
                return "Pre-Game";
            } else if ($scope.game.stack[$scope.game.stack.length-1] == "CoinToss" && team == null){
                return "Coin Toss";
            } else if ($scope.game.stack[$scope.game.stack.length-1] == "PostGame" && team == null){
                return "Post-Game";
            } else if ($scope.game.stack[$scope.game.stack.length-1] == "QuickSnap"){
                if (team != null && team == $scope.game.state.team_turn){
                    return "Quick Snap!";
                } else if (team == null){
                    if ($scope.game.state.half == 1 && team == null){
                        return "1st half";
                    } else if ($scope.game.state.half == 2 && team == null){
                        return "2nd half";
                    }
                }
            } else if ($scope.game.stack[$scope.game.stack.length-1] == "Blitz"){
                if (team != null && team == $scope.game.state.team_turn){
                    return "Blitz!";
                } else if (team == null){
                    if ($scope.game.state.half == 1 && team == null){
                        return "1st half";
                    } else if ($scope.game.state.half == 2 && team == null){
                        return "2nd half";
                    }
                }
            } else if ($scope.game.game_over && team == null){
                return "Game is Over";
            } else if ($scope.game.state.half == 1 && team == null){
                return "1st half";
            } else if ($scope.game.state.half == 2 && team == null){
                return "2nd half";
            }
            if (team != null && team){
                return $scope.game.state.home_state.turn + " / 8";
            } else if (team != null && !team){
                return $scope.game.state.away_state.turn + " / 8";
            }
            return "";
        };

        $scope.playerInFocus = function playerInFocus(team) {
            if ($scope.hover_player != null){
                let player = $scope.hover_player;
                if (player != null && team.team_id === $scope.teamOfPlayer(player).team_id){
                    return player;
                }
            }
            if ($scope.selected_square != null && $scope.selected_square.player != null){
                if (team.team_id === $scope.teamOfPlayer($scope.selected_square.player).team_id){
                    return $scope.selected_square.player;
                }
            }
            return null;
        };

        $scope.playerStateInFocus = function playerStateInFocus(team) {
            if ($scope.hover_player != null){
                let player = $scope.hover_player;
                if (player != null && team.team_id === $scope.teamOfPlayer(player).team_id){
                    if (team.team_id === $scope.game.home_team.team_id){
                        return $scope.game.state.home_state.player_states[player.player_id];
                    } else {
                        return $scope.game.state.away_state.player_states[player.player_id];
                    }
                }
            }
            if ($scope.selected_square != null && $scope.selected_square.player != null){
                let player = $scope.selected_square.player;
                if (team.team_id === $scope.teamOfPlayer($scope.selected_square.player).team_id){
                    if (team.team_id === $scope.game.home_team.team_id){
                        return $scope.game.state.home_state.player_states[player.player_id];
                    } else {
                        return $scope.game.state.away_state.player_states[player.player_id];
                    }
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
            if (action.action_type === "END_TURN" || action.action_type === "PASS"){
                $scope.resetSquares(true);
            }
            $scope.refreshing = true;
            GameService.act($scope.game.game_id, action).success(function(data) {
                $scope.game = data;
                console.log(data);
                $scope.setLocalState();
                $scope.setAvailablePositions();
                //$scope.updateMoveLines();
                $scope.refreshing = false;
                document.getElementById('gamelog').scrollTop = 0;
                let time = $scope.showReport($scope.game.reports[$scope.game.reports.length-1]) ? 10 : 0;
                $scope.checkForReload(time);
                $scope.saved = false;
            }).error(function(status, data) {
                $location.path("/#/");
            });
        };

        $scope.pickActionType = function pickActionType(action){
            if (action.action_type == "PLACE_BALL" && $scope.local_state.ball_position != null){
                let a = $scope.newAction(action.action_type);
                a.pos_to = $scope.local_state.ball_position;
                $scope.act(a);
            } else if (action.player_ids.length > 0 && $scope.selectedPlayer != null && action.player_ids.indexOf($scope.selectedPlayer().player_id) >= 0){
                let a = $scope.newAction(action.action_type);
                a.player_from_id = $scope.selectedPlayer().player_id;
                $scope.act(a);
            } else if (action.positions.length == 0){
                let a = $scope.newAction(action.action_type);
                $scope.act(a);
            }

        };

        $scope.pickDice = function pickDice(idx) {

            let a = $scope.newAction("SELECT_DIE");
            a.idx = idx;
            $scope.act(a);

        };

        $scope.showActionAsButton = function showActionAsButton(action) {
            if (action.action_type == "SELECT_DIE"){
                return false;
            }
            if (action.action_type !== "START_GAME" && action.action_type.indexOf("START_") > -1){
                return false;
            }
            // If no args -> show
            if (action.player_ids.length == 0 && action.positions.length == 0){
                return true;
            }
            if (action.player_ids.length > 0 && $scope.selected_square != null && $scope.selectedPlayer() != null && action.player_ids.indexOf($scope.selectedPlayer().player_id) >= 0 && action.positions.length == 0){
                return true;
            }
            if (action.player_ids.length == 0 && action.positions.length > 0){
                if (action.action_type == "PLACE_BALL" && $scope.local_state.ball_position != null){
                    return true;
                }
            }
            return false;
        };

        $scope.updateMoveLines = function updateMoveLines() {
            let lastX = null;
            let lastY = null;
            $( ".moveline" ).sort(function (a, b) {
                return parseInt(a.id.replace('moveline-', '')) > parseInt(b.id.replace('moveline-', ''));
            }).each(function() {
                let x = parseInt($( this ).attr('X'));
                let y = parseInt($( this ).attr('Y'));
                if (lastX !== null){
                    let yDir = y - lastY;
                    let xDir = x - lastX;
                    $( this ).attr('x1', 30 - xDir*30);
                    $( this ).attr('y1', 30 - yDir*30);
                    console.log(x)
                }
                lastX = x;
                lastY = y;
            });
        };

        // Get game-state when document is ready
        $( document ).ready(function() {
            GameService.get(id).success(function (data) {
                $scope.game = data;
                $scope.playersById = Object.assign({}, $scope.game.home_team.players_by_id, $scope.game.away_team.players_by_id);
                $scope.setLocalState();
                $scope.setAvailablePositions();
                //$scope.updateMoveLines();
                $scope.loading = false;
                console.log(data);
                $scope.checkForReload(2500);
                $scope.saved = false;
            }).error(function (status, data) {
                $location.path("/#/");
            });
        });


    }
]);