
appServices.factory('GameService', function($http) {
    return {
        get: function(id) {
            return $http.get(options.api.base_url + '/games/' + id);
        },
        
        findAll: function() {
            return $http.get(options.api.base_url + '/games/');
        },

        act: function(id, action) {
            return $http.put(options.api.base_url + '/games/' + id + '/act', {'game': {_id: id, is_published: newPublishState}});
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
