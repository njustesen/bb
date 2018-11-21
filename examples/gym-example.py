from bb.core.model import *
from bb.core.game import *
from bb.core.api import *
import numpy as np
import time
import gym


if __name__ == "__main__":

    # Create environment
    env = gym.make("FFAI-v1")

    # Create a random bot to take actions
    bot = RandomBot("My Random Bot")

    # Player 100 games
    for i in range(100):

        obs = env.reset()
        done = False

        # Take actions as long as game is not done
        while not done:

            # Take action using special get_game function - replace with you RL code
            game = env.get_game()
            action = bot.act(game)

            # Gym step function
            obs, reward, done, info = env.step(action)

