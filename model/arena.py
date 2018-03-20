import numpy as np


class Arena:

    def __init__(self, name, board):
        self.name = name
        self.board = board

    def get_empty_field(self):
        return np.zeros(self.board.shape)