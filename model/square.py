from math import sqrt


class Square:

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        if other is None or self is None:
            return False
        return self.x == other.x and self.y == other.x

    def distance(self, other, manhattan=True):
        if manhattan:
            return abs(other.x - self.x) + abs(other.y - self.y)
        else:
            return sqrt((other.x - self.x)**2 + (other.y - self.y)**2)

    def is_adjacent(self, other, manhattan=False):
        return self.distance(other, manhattan) == 1
