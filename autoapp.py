"""Application creator."""
from environs import Env

from aggrep import create_app
from config import DevelopmentConfig, ProductionConfig, TestingConfig

env = Env()
env.read_env()

environment = env.str("FLASK_ENV", "production")

config_map = dict(
    production=ProductionConfig, development=DevelopmentConfig, testing=TestingConfig
)

config = config_map.get(environment, ProductionConfig)

app = create_app(config)
