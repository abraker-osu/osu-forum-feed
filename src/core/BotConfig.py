from typing import Any
import yaml


class BotConfig(dict):
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super(BotConfig, cls).__new__(cls, *args, **kwargs)

        return cls.__instance

    def __init__(self, *args, **kwargs):
        with open('config.yaml', 'r') as f:
            dict.__init__(self, yaml.safe_load(f))


BotConfig: dict[str, Any] = BotConfig().copy()
