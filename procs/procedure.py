from abc import ABC, abstractmethod


class Procedure(ABC):
 
    def __init__(self, game):
        self.game = game
        self.game.stack.push(self)
        super().__init__()

    @abstractmethod
    def step(self, action):
        pass

