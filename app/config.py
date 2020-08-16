import os

from dotenv import load_dotenv


load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


class Config:
    GITHUB_ACCESS_TOKEN = os.environ['GITHUB_ACCESS_TOKEN']
    MONGODB_URL = os.environ['MONGODB_URL']
    SENTRY_DSN = os.environ.get('SENTRY_DSN')


def get_config():
    return Config
