from abc import ABC, abstractmethod


class Procedure(ABC):
 
    def __init__(self, procedures=[]):
        super().__init__()
    
    @abstractmethod
    def step(self, action):
        pass

