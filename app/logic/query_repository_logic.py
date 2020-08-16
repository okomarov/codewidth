import io
import zipfile

import requests


# https://github.com/github/gitignore/blob/master/Python.gitignore
python_gitignore_tokens = [
    '__pycache__/', '.Python', 'build/', 'develop-eggs/', 'dist/', 'downloads/',
    'eggs/', '.eggs/', 'lib/', 'lib64/', 'parts/', 'sdist/', 'var/', 'wheels/',
    'share/python-wheels/', '.egg-info/', 'htmlcov/', '.tox/', '.nox/', '.coverage',
    '.cache', '.hypothesis/', '.pytest_cache/', 'cover/', 'local_settings.py',
    'instance/', '.webassets-cache', '.scrapy', 'docs/_build/', '.pybuilder/',
    'target/', '.ipynb_checkpoints', 'profile_default/', 'ipython_config.py',
    '__pypackages__/', 'celerybeat-schedule', '.sage.py', '.env', '.venv', 'env/',
    'venv/', 'ENV/', 'env.bak/', 'venv.bak/', '/site', '.mypy_cache/', '.pyre/',
    '.pytype/', 'cython_debug/']


def _path_has_ignored_tokens(path):
    return any(token in path for token in python_gitignore_tokens)


def is_python_file_of_interest(git_tree_element):
    return (
        git_tree_element.path.endswith('.py') and
        git_tree_element.size > 0 and
        not _path_has_ignored_tokens(git_tree_element.path))


def list_python_files_of_interest(git_repo):
    tree = git_repo.get_git_tree(git_repo.default_branch, recursive=True).tree
    return [element for element in tree if is_python_file_of_interest(element)]


def has_python_language_above(git_repo, threshold=0.6):
    languages = git_repo.get_languages()
    total = sum(languages.values())
    return languages['Python']/total > threshold


def get_repo_metadata(git_repo):
    def exclude_api_props(data_dict):
        new_data = {}
        for k, v in data_dict.items():
            if isinstance(v, dict):
                new_data[k] = exclude_api_props(v)
            elif isinstance(v, str) and v.startswith('https://api'):
                continue
            else:
                new_data[k] = v
        return new_data

    return exclude_api_props(git_repo.raw_data)


def download_repo(git_repo, selected_files=None):
    zip_url = f'{git_repo.html_url}/archive/{git_repo.default_branch}.zip'
    request = requests.get(zip_url)
    archive = zipfile.ZipFile(io.BytesIO(request.content))
    destination = f'app/temp/{git_repo.name}'

    if selected_files is not None:
        selected_files = [
            file for file in archive.namelist()
            if any(pattern in file for pattern in selected_files)]

    archive.extractall(destination, members=selected_files)

    return f'{destination}/{git_repo.name}-{git_repo.default_branch}'
