from abc import ABC, abstractmethod
import random
from enum import Enum


class Die(ABC):

    @abstractmethod
    def get_value(self):
        pass


class DiceRoll():

    def __init__(self, dice):
        self.dice = dice
        self.sum = -1

    def get_values(self):
        return [d.get_value for d in self.dice]

    def get_sum(self):
        if sum >= 0:
            return sum
        sum = 0
        for d in self.dice:
            assert not isinstance(d, BBDie)
            sum += d.get_value()
        return sum


class D6(Die):

    def __init__(self):
        self.value = random.randint(1, 6)

    def get_value(self):
        return self.value


class D9(Die):

    def __init__(self):
        self.value = random.randint(1, 9)

    def get_value(self):
        return self.value


class BBDieResult(Enum):
    ATTACKER_DOWN = 1
    BOTH_DOWN = 2
    PUSH = 3
    DEFENDER_STUMBLES = 4
    DEFENDER_DOWN = 5


class BBDie(Die):

    def __init__(self):
        r = random.randint(1, 6)
        if r == 6:
            r = 3
        self.value = BBDieResult(r)

    def get_value(self):
        return self.value
