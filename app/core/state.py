
from functools import lru_cache

from app.core.config import Config, get_config

class State:
    def __init__(self, config: Config) -> None:
        pass

    def transfer(self, state):
        for key, value in self.__dict__.items():
            setattr(state, key, value)

@lru_cache
def get_state():
    return State(get_config())