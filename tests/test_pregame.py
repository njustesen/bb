import unittest
from bb import api


class TestPregame(unittest.TestCase):

    def test_init(self):
        game = api.new_game()
        assert game.state.home_state.score == 0 and game.state.away_state.score == 0
        assert len(game.state.field.player_positions) == 0

if __name__ == '__main__':
    unittest.main()