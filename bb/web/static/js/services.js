
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
