
appServices.factory('GameService', function($http) {
    return {
        get: function(id) {
            return $http.get(options.api.base_url + '/games/' + id);
        },
        
        findAll: function() {
            return $http.get(options.api.base_url + '/games/');
        },

        act: function(id, action) {
            return $http.post(options.api.base_url + '/games/' + id + '/act', {'action': action});
        },

        delete: function(id) {
            return $http.delete(options.api.base_url + '/games/' + id + "/delete");
        },

        create: function(game) {
            return $http.put(options.api.base_url + '/game/create', {'game': game});
        }

    };
});


appServices.factory('TeamService', function($http) {
    return {
        findAll: function() {
            return $http.get(options.api.base_url + '/teams/');
        }
    };
});

appServices.factory('GameLogService', function() {

    return {
        log_texts: {
            'SPECTATORS': "<n> spectators showed up to watch the game.",
            'FAME': "<team> has +<n> Fan Advantage ModifiEr (FAME).",
            'HEADS_WON': "Heads! <away_team> won the coin toss.",
            'HEADS_LOSS': "Heads! <home_team> won the coin toss.",
            'TAILS_WON': "Tails! <away_team> won the coin toss.",
            'TAILS_LOSS': "Tails! <home_team> won the coin toss.",
            'HOME_RECEIVE': "<home_team> will receive the ball.",
            'AWAY_RECEIVE': "<away_team> will receive the ball.",
            'WEATHER_SWELTERING_HEAT': "Sweltering Heat: It’s so hot and humid that some players collapse from heat exhaustion. Roll a D6 for each player on the pitch at the end of a drive. On a roll of 1 the player collapses and may not be set up for the next kick-off.",
            'WEATHER_VERY_SUNNY': "Very Sunny: A glorious day, but the blinding sunshine causes a -1 modifier on all passing rolls.",
            'WEATHER_NICE': "Nice: Perfect Blood Bowl weather.",
            'WEATHER_POURING_RAIN': "Pouring Rain: It’s raining, making the ball slippery and difficult to hold. A -1 modifier applies to all catch, intercept, or pick-up rolls.",
            'WEATHER_BLIZZARD': "Blizzard: It’s cold and snowing! The ice on the pitch means that any player attempting to move an extra square (GFI) will slip and be Knocked Down on a roll of 1-2, while the snow means that only quick or short passes can be attempted.",
            'ILLEGAL_SETUP_NUM': 'Illegal Setup: You must field between 3 and 11 players.',
            'ILLEGAL_SETUP_SCRIMMAGE': 'Illegal Setup: Min. 3 players on the line of scrimmage!',
            'ILLEGAL_SETUP_WINGS': 'Illegal Setup: Max. 2 players on each wing!',
            'BALL_PLACED': 'Ball is ready to be kicked.',
            'KICKOFF_GET_THE_REF': "Get the Ref: The fans exact gruesome revenge on the referee for some of the dubious decisions he has made, either during this match or in the past. His replacement is so intimidated that he can be more easily persuaded to look the other way. Each team receives 1 additional Bribe to use during this game. A Bribe allows you to attempt to ignore one call by the referee for a player who has committed a foul to be sent off, or a player armed with a secret weapon to be banned from the match. Roll a D6: on a roll of 2-6 the bribe is effective (preventing a turnover if the player was ejected for fouling), but on a roll of 1 the bribe is wasted and the call still stands! Each bribe may be used once per match.",
            'KICKOFF_RIOT': "Riot: The trash talk between two opposing players explodes and rapidly degenerates, involving the rest of the players. If the receiving team’s turn marker is on turn 7 for the half, both teams move their turn marker back one space as the referee resets the clock back to before the fight started. If the receiving team has not yet taken a turn this half the referee lets the clock run on during the fight and both teams’ turn markers are moved forward one space. Otherwise roll a D6. On a 1-3, both teams’ turn markers are moved forward one space. On a 4-6, both team’s turn markers are moved back one space.",
            'KICKOFF_PERFECT_DEFENSE': "Perfect Defence: The kicking team’s coach may reorganize his players – in other words he can set them up again into another legal defence. The receiving team must remain in the set-up chosen by their coach.",
            'KICKOFF_HIGH_KICK': "High Kick: The ball is kicked very high, allowing a player on the receiving team time to move into the perfect position to catch it. Any one player on the receiving team who is not in an opposing player’s tackle zone may be moved into the square where the ball will land no matter what their MA may be, as long as the square is unoccupied.",
            'KICKOFF_CHEERING_FANS': "Cheering Fans: Each coach rolls a D3 and adds their team’s FAME (see page 18) and the number of cheerleaders on their team to the score. The team with the highest score is inspired by their fans' cheering and gets an extra re-roll this half. If both teams have the same score, then both teams get a re-roll.",
            'KICKOFF_CHANGING_WHEATHER': "Changing Weather: Make a new roll on the Weather table (see page 20). Apply the new Weather roll. If the new Weather roll was a ‘Nice’ result, then a gentle gust of wind makes the ball scatter one extra square in a random direction before landing.",
            'KICKOFF_BRILLIANT_COACHING': "Brilliant Coaching: Each coach rolls a D3 and adds their FAME (see page 18) and the number of assistant coaches on their team to the score. The team with the highest total gets an extra team re-roll this half thanks to the brilliant instruction provided by the coaching staff. In case of a tie both teams get an extra team re-roll.",
            'KICKOFF_QUICK_SNAP': "Quick Snap! The offence start their drive a fraction before the defence is ready, catching the kicking team flat-footed. All of the players on the receiving team are allowed to move one square. This is a free move and may be made into any adjacent empty square, ignoring tackle zones. It may be used to enter the opposing half of the pitch.",
            'KICKOFF_BLITZ': "Blitz! The defence start their drive a fraction before the offence is ready, catching the receiving team flat-footed. The kicking team receives a free ‘bonus’ turn: however, players that are in an enemy tackle zone at the beginning of this free turn may not perform an Action. The kicking team may use team re-rolls during a Blitz. If any player suffers a turnover then the bonus turn ends immediately.",
            'KICKOFF_THROW_A_ROCK': "Throw a Rock: An enraged fan hurls a large rock at one of the players on the opposing team. Each coach rolls a D6 and adds their FAME (see page 18) to the roll. The fans of the team that rolls higher are the ones that threw the rock. In the case of a tie a rock is thrown at each team! Decide randomly which player in the other team was hit (only players on the pitch are eligible) and roll for the effects of the injury straight away. No Armour roll is required.",
            'KICKOFF_PITCH_INVASION': "Pitch Invasion: Both coaches roll a D6 for each opposing player on the pitch and add their FAME (see page 18) to the roll. If a roll is 6 or more after modification then the player is Stunned (players with the Ball & Chain skill are KO'd). A roll of 1 before adding FAME will always have no effect.",
            'GET_THE_REF': "GET_THE_REF",
            'RIOT': "<n> turns added to this half.",
            'HIGH_KICK': "HIGH_KICK",
            'CHEERING_FANS': "CHEERING_FANS",
            'BRILLIANT_COACHING': "BRILLIANT_COACHING",
            'THROW_A_ROCK': "THROW_A_ROCK",
            'PITCH_INVASION': "PITCH_INVASION",
            'PITCH_INVASION_ROLL': "PITCH_INVASION_ROLL",
            'NOTHING': "NOTHING",
            'KICK_IN_BOUNDS': "The ball was kicked.",
            'KICK_OUT_OF_BOUNDS': "Ball kicked out of bounds.",
            'BALL_HIT_GROUND': "BALL_HIT_GROUND",
            'BALL_HIT_PLAYER': "BALL_HIT_PLAYER",
            'SETUP_DONE': "<team> is done setting up.",
            'KNOCKED_DOWN': "KNOCKED_DOWN",
            'ARMOR_BROKEN': "ARMOR_BROKEN",
            'ARMOR_NOT_BROKEN': "ARMOR_NOT_BROKEN",
            'STUNNED': "STUNNED",
            'KNOCKED_OUT': "KNOCKED_OUT",
            'BADLY_HURT': "BADLY_HURT",
            'INTERCEPTION': "INTERCEPTION",
            'BALL_CAUGhT': "BALL_CAUGhT",
            'BALL_DROPPED': "BALL_DROPPED",
            'FAILED_DODGE': "FAILED_DODGE",
            'SUCCESSFUL_DODGE': "SUCCESSFUL_DODGE",
            'FAILED_GFI': "FAILED_GFI",
            'SUCCESSFUL_GFI': "SUCCESSFUL_GFI",
            'FAILED_PICKUP': "FAILED_PICKUP",
            'SUCCESSFUL_PICKUP': "SUCCESSFUL_PICKUP",
            'COMPLETE_PASS': "COMPLETE_PASS",
            'INCOMPLETE_PASS': "INCOMPLETE_PASS",
            'COMPLETE_HANDOFF': "COMPLETE_HANDOFF",
            'INCOMPLETE_HANDOFF': "INCOMPLETE_HANDOFF",
            'END_PLAYER_TURN': "END_PLAYER_TURN",
            'MOVE_ACTION_STARTED': "MOVE_ACTION_STARTED",
            'BLOCK_ACTION_STARTED': "BLOCK_ACTION_STARTED",
            'BLITZ_ACTION_STARTED': "BLITZ_ACTION_STARTED",
            'PASS_ACTION_STARTED': "PASS_ACTION_STARTED",
            'FOUL_ACTION_STARTED': "FOUL_ACTION_STARTED",
            'HANDOFF_ACTION_STARTED': "HANDOFF_ACTION_STARTED",
            'END_OF_GAME': "END_OF_GAME",
            'END_OF_PREGAME': "END_OF_PREGAME",
            'END_OF_TURN': "END_OF_TURN",
            'END_OF_HALF': "END_OF_HALF",
            'TOUCHDOWN': "TOUCHDOWN",
            'TURNOVER': "TURNOVER",
            'CASUALTY': "CASUALTY",
            'APOTHECARY_USED_KO': "APOTHECARY_USED_KO",
            'APOTHECARY_USED_CASUALTY': "APOTHECARY_USED_CASUALTY",
            'CASUALTY_APOTHECARY': "CASUALTY_APOTHECARY",
            'DAUNTLESS_USED': "DAUNTLESS_USED",
            'PUSHED_INTO_CROWD': "PUSHED_INTO_CROWD",
            'PUSHED': "PUSHED",
            'ACCURATE_PASS': "ACCURATE_PASS",
            'INACCURATE_PASS': "INACCURATE_PASS",
            'FUMBLE': "FUMBLE",
            'CATCH_FAILED': "CATCH_FAILED",
            'BALL_SCATTER': "BALL_SCATTER"
        }
    };
});

appServices.factory('IconService', function() {

    return {
        playerIcons: {
            'Human': {
                'Lineman': 'hlineman',
                'Blitzer': 'hblitzer',
                'Thrower': 'hthrower',
                'Catcher': 'hcatcher',
                'Ogre': 'ogre'
            },
            'Orc': {
                'Lineman': 'olineman',
                'Blitzer': 'oblitzer',
                'Thrower': 'othrower',
                'Black Orc Blocker': 'oblackorc',
                'Troll': 'troll',
                'Goblin': 'goblin'
            }
        }
    };
});
