import unittest
from bb import api
from bb import load


class TestLoaders(unittest.TestCase):

    def test_ruleset_loader(self):
        name = 'LRB5-Experimental'
        ruleset = load.get_rule_set(name)
        assert ruleset is not None
        assert ruleset.name == name

    def test_team_loader(self):
        team_name = 'reikland_reivers'
        ruleset_name = 'LRB5-Experimental'
        ruleset = load.get_rule_set(ruleset_name)
        team = load.get_team(team_name, ruleset)
        assert team is not None
        assert team.name == "Reikland Reivers"

    def test_arena(self):
        name = 'bb_pitch'
        arena = load.get_arena(name)
        assert arena is not None
        assert len(arena.board) == 15 + 2
        assert len(arena.board[0]) == 26 + 2


if __name__ == '__main__':
    unittest.main()