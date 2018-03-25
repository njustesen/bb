from core import Procedure, GFI, Armor



class Foul(Procedure):

    def __init__(self, game, home, player_from, player_to, gfi):
        super().__init__(game)
        self.home = home
        self.player_from = player_from
        self.player_to = player_to
        self.pos_from = self.game.state.field.get_player_position(player_from.player_id)
        self.pos_to = self.game.state.field.get_player_position(self.player_to)
        self.gfi = gfi
        self.waiting_gfi = False

    def step(self, action):

        # GfI
        if self.gfi:
            self.gfi = False
            GFI(self.game, self.home, self.player_from, self.pos_from, self.pos_to)
            return False

        # Assists
        assists_from = self.game.state.field.assists(self.home, self.player_from, self.player_to, ignore_guard=True)
        assists_to = self.game.state.field.assists(not self.home, self.player_to, self.player_from, ignore_guard=True)
        modifier = assists_from - assists_to

        # Armor roll
        Armor(self.game, self.home, self.player_to.player_id, modifiers=modifier, opp_player_id=self.player_from.player_id, foul=True)

        return True