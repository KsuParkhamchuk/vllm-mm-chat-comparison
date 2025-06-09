import os
from dotenv import load_dotenv

class Config():
    MODEL1_ENDPOINT=""
    MODEL2_ENDPOINT=""
    MODEL1_NAME=""
    MODEL2_NAME=""

    @classmethod
    def from_env (cls):
        load_dotenv()

        config = cls()
        config.MODEL1_ENDPOINT = os.getenv("MODEL1_ENDPOINT", cls.MODEL1_ENDPOINT)
        config.MODEL2_ENDPOINT = os.getenv("MODEL2_ENDPOINT", cls.MODEL2_ENDPOINT)
        config.MODEL1_NAME = os.getenv("MODEL1_NAME", cls.MODEL1_NAME)
        config.MODEL2_NAME = os.getenv("MODEL2_NAME", cls.MODEL2_NAME)

        return config

config = Config.from_env()
