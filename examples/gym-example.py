from bb.web.api import *
import gym


if __name__ == "__main__":

    # Create environment
    # env = gym.make("FFAI-v1")
    # env = gym.make("FFAI-7-v1")
    # env = gym.make("FFAI-5-v1")
    env = gym.make("FFAI-3-v1")

    # Set seed for reproducibility
    seed = 0
    env.seed(seed)

    # Create a random bot to take actions
    bot = RandomBot("My Random Bot", seed=seed)

    # Play 10 games
    steps = 0
    for i in range(10):

        obs = env.reset()
        done = False

        # Take actions as long as game is not done
        while not done:

            # Take action using special get_game function - replace with you RL code
            game = env.get_game()
            action = bot.act(game)

            # Gym step function
            obs, reward, done, info = env.step(action)
            steps += 1
            print(steps)

            # Render
            env.render(feature_layers=False)

    print(steps)
