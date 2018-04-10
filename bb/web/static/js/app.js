'use strict';

var app = angular.module('app', ['ngRoute', 'appControllers', 'appServices', 'appDirectives']);

var appServices = angular.module('appServices', []);
var appControllers = angular.module('appControllers', []);
var appDirectives = angular.module('appDirectives', []);

var options = {};
options.api = {};
options.api.base_url = "http://127.0.0.1:5000";


app.config(['$locationProvider', '$routeProvider', 
  function($location, $routeProvider) {
    $routeProvider.
        when('/', {
            templateUrl: 'static/partials/post.list.html',
            controller: 'PostListCtrl'
        }).
        when('/post/:id', {
            templateUrl: 'static/partials/post.view.html',
            controller: 'PostViewCtrl'
        }).
        when('/tag/:tagName', {
            templateUrl: 'static/partials/post.list.html',
            controller: 'PostListTagCtrl'
        }).
        when('/admin', {
            templateUrl: 'static/partials/admin.post.list.html',
            controller: 'AdminPostListCtrl',
            access: { requiredAuthentication: true }
        }).
        when('/admin/post/create', {
            templateUrl: 'static/partials/admin.post.create.html',
            controller: 'AdminPostCreateCtrl',
            access: { requiredAuthentication: true }
        }).
        when('/admin/post/edit/:id', {
            templateUrl: 'static/partials/admin.post.edit.html',
            controller: 'AdminPostEditCtrl',
            access: { requiredAuthentication: true }
        }).
        when('/admin/register', {
            templateUrl: 'static/partials/admin.register.html',
            controller: 'AdminUserCtrl'
        }).
        when('/admin/login', {
            templateUrl: 'static/partials/admin.signin.html',
            controller: 'AdminUserCtrl'
        }).
        when('/admin/logout', {
            templateUrl: 'static/partials/admin.logout.html',
            controller: 'AdminUserCtrl',
            access: { requiredAuthentication: true }
        }).
        otherwise({
            redirectTo: '/'
        });
}]);


app.config(function ($httpProvider) {
    $httpProvider.interceptors.push('TokenInterceptor');
});

app.run(function($rootScope, $location, $window, AuthenticationService) {
    $rootScope.$on("$routeChangeStart", function(event, nextRoute, currentRoute) {
        //redirect only if both isAuthenticated is false and no token is set
        if (nextRoute != null && nextRoute.access != null && nextRoute.access.requiredAuthentication 
            && !AuthenticationService.isAuthenticated && !$window.sessionStorage.token) {

            $location.path("/admin/login");
        }
    });
});