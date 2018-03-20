from model.playerstate import PlayerState


class GameState:

    def __init__(self, game):
        self.home_score = 0
        self.away_score = 0
        self.half = 1
        self.turn_home = 0
        self.turn_away = 0
        self.kicking_team = None
        self.field = game.arena.get_empty_field()
        self.home_player_states = {player.id: PlayerState.READY for player in game.home.players}
        self.away_player_states = {player.id: PlayerState.READY for player in game.away.players}
