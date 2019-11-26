"""Application creator."""
from environs import Env

from aggrep import create_app
from config import DevelopmentConfig, ProductionConfig

env = Env()
env.read_env()

environment = env.str("FLASK_ENV")

config = ProductionConfig
if environment == "development":
    config = DevelopmentConfig

app = create_app(config)
