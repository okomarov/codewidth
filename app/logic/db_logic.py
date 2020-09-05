from clients import mongodb_client


def insert_one(document):
    collection = mongodb_client.get_repos_collection()
    return collection.insert_one(document)


def check_exists(criteria):
    collection = mongodb_client.get_repos_collection()
    return collection.count_documents(criteria, limit=1) > 0


def get_names():
    collection = mongodb_client.get_repos_collection()
    return collection.distinct('name')
