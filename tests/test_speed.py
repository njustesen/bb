import time
from bb.core import api
from bb.core.model import *


def test_speed():
    game = api.new_game("a1", "b2")
    n = 0
    print("Start")
    start = time.time()
    while not game.game_over:
        if len(game.available_actions) == 0:
            game.step(None)
            #print("None")
        else:
            action_choice = random.sample(game.available_actions, 1)[0]
            player_from_id = random.sample(action_choice.player_ids, 1)[0] if len(action_choice.player_ids) > 0 else None
            player_to_id = random.sample(action_choice.player_ids, 1)[0] if len(action_choice.player_ids) > 0 else None
            pos_from = random.sample(action_choice.positions, 1)[0] if len(action_choice.positions) > 0 else None
            pos_to = random.sample(action_choice.positions, 1)[0] if len(action_choice.positions) > 0 else None
            idx = random.sample(action_choice.indexes, 1)[0] if len(action_choice.indexes) > 0 else 0

            action = Action(action_choice.action_type, pos_from=pos_from, pos_to=pos_to, player_from_id=player_from_id, player_to_id=player_to_id, idx=idx)
            #print(action.to_simple())
            game.step(action)
        n += 1
    end = time.time()
    print("Done " + str((end - start)))
    print("Per step " + str((end - start)/n))

if __name__ == '__main__':
    test_speed()
