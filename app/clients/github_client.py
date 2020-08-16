from github import Github

from config import get_config


def get_client():
    cfg = get_config()
    return Github(cfg.GITHUB_ACCESS_TOKEN)


def get_repos_by_language(language):
    client = get_client()
    repos = client.search_repositories(query=f'language:{language}')
    return repos
