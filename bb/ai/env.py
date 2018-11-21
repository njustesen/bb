import gym
from bb.core.game import *
from bb.core.load import *
from bb.ai.bots import RandomBot
from bb.ai.layers import *
from gym import error, spaces, utils
from copy import deepcopy
import random
import uuid


class FFAIEnv(gym.Env):

    def __init__(self, config, home_team, away_team, opp_actor=None):
        self.__version__ = "0.0.1"
        self.config = config
        self.game = None
        self.team_id = None
        self.ruleset = get_rule_set(config.ruleset)
        self.home_team = home_team
        self.away_team = away_team
        self.actor = Agent("Gym Learner", human=True)
        self.opp_actor = opp_actor if opp_actor is not None else RandomBot("Random")
        self.layers = [
            OccupiedLayer(),
            OwnPlayerLayer(),
            OppPlayerLayer(),
            OwnTackleZoneLayer(),
            OppTackleZoneLayer(),
            ReadyLayer(),
            DownLayer(),
            UsedLayer(),
            AvailablePlayerLayer(),
            AvailablePositionLayer(),
            MALayer(),
            STLayer(),
            AGLayer(),
            AVLayer(),
            MovemenLeftLayer(),
            BallLayer(),
            OwnHalfLayer(),
            OwnTouchdownLayer(),
            OppTouchdownLayer(),
            SkillLayer(Skill.BLOCK),
            SkillLayer(Skill.DODGE),
            SkillLayer(Skill.SURE_HANDS),
            SkillLayer(Skill.PASS),
            SkillLayer(Skill.BLOCK)
        ]

    def step(self, action):
        self.game.step(action)
        reward = 1 if self.game.get_winner() == self.actor else 0
        team = self.game.state.home_team if self.team_id == self.home_team.team_id else self.game.state.away_team
        opp_team = self.game.state.home_team if self.team_id != self.home_team.team_id else self.game.state.away_team
        info = {
            'cas_inflicted': len(self.game.get_casualties(team)),
            'opp_cas_inflicted': len(self.game.get_casualties(opp_team)),
            'touchdowns': team.state.score,
            'opp_touchdowns': opp_team.state.score,
            'half': self.game.state.round,
            'round': self.game.state.round
        }
        return self._observation(self.game), reward, self.game.state.game_over, info

    def get_game(self):
        return self.game

    def _observation(self, game):
        obs = {
            'spatial': {},
            'non-spatial': {}
        }
        for layer in self.layers:
            obs['spatial'][layer.name()] = layer.produce(game)

        active_team = game.state.available_actions[0].team if len(game.state.available_actions) > 0 else None
        opp_team = game.get_opp_team(active_team) if active_team is not None else None

        obs['non-spatial']['half'] = game.state.half - 1.0
        obs['non-spatial']['round'] = game.state.round / 8.0
        obs['non-spatial']['sweltering heat'] = 1.0 if game.state.weather == WeatherType.SWELTERING_HEAT else 0.0
        obs['non-spatial']['very sunny'] = 1.0 if game.state.weather == WeatherType.VERY_SUNNY else 0.0
        obs['non-spatial']['nice'] = 1.0 if game.state.weather.value == WeatherType.NICE else 0.0
        obs['non-spatial']['pouring rain'] = 1.0 if game.state.weather.value == WeatherType.POURING_RAIN else 0.0
        obs['non-spatial']['blizzard'] = 1.0 if game.state.weather.value == WeatherType.BLIZZARD else 0.0

        obs['non-spatial']['own turn'] = 1.0 if game.state.current_team == active_team else 0.0
        obs['non-spatial']['kicking first half'] = 1.0 if game.state.kicking_first_half == active_team else 0.0
        obs['non-spatial']['kicking this drive'] = 1.0 if game.state.kicking_this_drive == active_team else 0.0
        obs['non-spatial']['own reserves'] = len(game.get_reserves(active_team)) / 16.0 if active_team is not None else 0.0
        obs['non-spatial']['own kods'] = len(game.get_kods(active_team)) / 16.0 if active_team is not None else 0.0
        obs['non-spatial']['own casualites'] = len(game.get_casualties(active_team)) / 16.0 if active_team is not None else 0.0
        obs['non-spatial']['opp reserves'] = len(game.get_reserves(game.get_opp_team(active_team))) / 16.0 if active_team is not None else 0.0
        obs['non-spatial']['opp kods'] = len(game.get_kods(game.get_opp_team(active_team))) / 16.0 if active_team is not None else 0.0
        obs['non-spatial']['opp casualties'] = len(game.get_casualties(game.get_opp_team(active_team))) / 16.0 if active_team is not None else 0.0

        obs['non-spatial']['own score'] = active_team.state.score / 16.0 if active_team is not None else 0.0
        obs['non-spatial']['own turn'] = active_team.state.turn / 8.0 if active_team is not None else 0.0
        obs['non-spatial']['own starting rerolls'] = active_team.state.rerolls_start / 8.0 if active_team is not None else 0.0
        obs['non-spatial']['own rerolls left'] = active_team.state.rerolls / 8.0 if active_team is not None else 0.0
        obs['non-spatial']['own ass coaches'] = active_team.state.ass_coaches / 8.0 if active_team is not None else 0.0
        obs['non-spatial']['own cheerleaders'] = active_team.state.cheerleaders / 8.0 if active_team is not None else 0.0
        obs['non-spatial']['own bribes'] = active_team.state.bribes / 4.0 if active_team is not None else 0.0
        obs['non-spatial']['own babes'] = active_team.state.babes / 4.0 if active_team is not None else 0.0
        obs['non-spatial']['own apothecary available'] = 1.0 if active_team is not None and active_team.state.apothecary_available else 0.0
        obs['non-spatial']['own reroll available'] = 1.0 if active_team is not None and not active_team.state.reroll_used else 0.0
        obs['non-spatial']['own fame'] = active_team.state.fame if active_team is not None else 0.0

        obs['non-spatial']['opp score'] = opp_team.state.score / 16.0 if opp_team is not None else 0.0
        obs['non-spatial']['opp turn'] = opp_team.state.turn / 8.0 if opp_team is not None else 0.0
        obs['non-spatial']['opp starting rerolls'] = opp_team.state.rerolls_start / 8.0 if opp_team is not None else 0.0
        obs['non-spatial']['opp rerolls left'] = opp_team.state.rerolls / 8.0 if opp_team is not None else 0.0
        obs['non-spatial']['opp ass coaches'] = opp_team.state.ass_coaches / 8.0 if opp_team is not None else 0.0
        obs['non-spatial']['opp cheerleaders'] = opp_team.state.cheerleaders / 8.0 if opp_team is not None else 0.0
        obs['non-spatial']['opp bribes'] = opp_team.state.bribes / 4.0 if opp_team is not None else 0.0
        obs['non-spatial']['opp babes'] = opp_team.state.babes / 4.0 if opp_team is not None else 0.0
        obs['non-spatial']['own apothecary available'] = 1.0 if opp_team is not None and opp_team.state.apothecary_available else 0.0
        obs['non-spatial']['opp reroll available'] = 1.0 if opp_team is not None and not opp_team.state.reroll_used else 0.0
        obs['non-spatial']['opp fame'] = opp_team.state.fame if opp_team is not None else 0.0

        obs['non-spatial']['blitz available'] = 1.0 if game.is_blitz_available() else 0.0
        obs['non-spatial']['pass available'] = 1.0 if game.is_pass_available() else 0.0
        obs['non-spatial']['handoff available'] = 1.0 if game.is_handoff_available() else 0.0
        obs['non-spatial']['foul available'] = 1.0 if game.is_foul_available() else 0.0
        obs['non-spatial']['is blitz'] = 1.0 if game.is_blitz() else 0.0
        obs['non-spatial']['is quick snap'] = 1.0 if game.is_quick_snap() else 0.0

        return obs

    def reset(self):
        if random.random() >= 0.5:
            self.team_id = self.home_team.team_id
            home_agent = self.actor
            away_agent = self.opp_actor
        else:
            self.team_id = self.away_team.team_id
            home_agent = self.opp_actor
            away_agent = self.actor
        self.game = Game(game_id=str(uuid.uuid1()),
                         home_team=self.home_team,
                         away_team=self.away_team,
                         home_agent=home_agent,
                         away_agent=away_agent,
                         config=self.config,
                         ruleset=self.ruleset)
        self.game.init()
        return self._observation(self.game)

    def render(self, mode='human'):
        return NotImplementedError("Will appera in version 0.0.2")

    def close(self):
        self.game = None

