import os
from dotenv import load_dotenv

class Config():
    """Config class allows easier models and endpoints configuration"""
    MODEL1_ENDPOINT=""
    MODEL2_ENDPOINT=""
    MODEL1=""
    MODEL2=""

    @classmethod
    def from_env (cls):
        load_dotenv()

        cnf = cls()
        cnf.MODEL1_ENDPOINT = os.getenv("MODEL1_ENDPOINT", cls.MODEL1_ENDPOINT)
        cnf.MODEL2_ENDPOINT = os.getenv("MODEL2_ENDPOINT", cls.MODEL2_ENDPOINT)
        cnf.MODEL1 = os.getenv("MODEL1", cls.MODEL1)
        cnf.MODEL2 = os.getenv("MODEL2", cls.MODEL2)

        return config

config = Config.from_env()
