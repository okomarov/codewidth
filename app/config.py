import os

from dotenv import load_dotenv


load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


class Config:
    CODE_BLOCK_LEN_HARDCODED_DATA = 100
    GITHUB_ACCESS_TOKEN = os.environ['GITHUB_ACCESS_TOKEN']
    MONGODB_URL = os.environ['MONGODB_URL']
    REPO_SIZE_CUTOFF_IN_KB = 5e5
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    SENTRY_MAX_STRING_LENGTH = 2048


def get_config():
    return Config
