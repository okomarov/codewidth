import pymongo

from config import get_config


def get_client():
    cfg = get_config()
    return pymongo.MongoClient(cfg.MONGODB_URL)


def get_repos_collection():
    mongodb = get_client()
    db = mongodb.get_default_database()
    return db.get_collection('repos')
