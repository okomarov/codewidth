from datetime import datetime
import shutil

import sentry_sdk

from clients import github_client
from config import get_config
from logic import code_analysis_logic
from logic import db_logic
from logic import query_repository_logic


cfg = get_config()
sentry_sdk.init(dsn=cfg.SENTRY_DSN, traces_sample_rate=1.0)
sentry_sdk.utils.MAX_STRING_LENGTH = 2048


if __name__ == '__main__':
    repos = github_client.get_repos_by_language(language='python')
    for repo in repos:
        name = repo.full_name
        if db_logic.check_exists({'name': name}):
            continue

        files_map = query_repository_logic.list_python_files_of_interest(repo)
        num_files = len(files_map)
        files_of_interest = [k for k, v in files_map.items() if v == 1]
        num_files_interest = len(files_of_interest)

        metrics = {
            'name': name,
            'created_at': datetime.utcnow().isoformat(),
            'num_files': num_files,
            'num_files_interest': num_files_interest,
            'state': 'basic'}
        print(metrics)

        if num_files_interest < 1:
            db_logic.insert_one(metrics)
            continue

        metrics['github'] = query_repository_logic.get_repo_metadata(repo)
        metrics['github'].update({'languages': repo.get_languages()})
        metrics['state'] = 'github'

        if metrics['github']['size']/num_files_interest > 1e5:
            db_logic.insert_one(metrics)
            continue

        folder = query_repository_logic.download_repo(
            repo, selected_files=files_of_interest)
        file_metrics = code_analysis_logic.calculate_metrics(folder)
        metrics.update(code_analysis_logic.consolidate_repo_metrics(file_metrics))
        if metrics['num_files_error'] < metrics['num_files_interest']:
            metrics['files'] = file_metrics
            metrics['state'] = 'full'

        db_logic.insert_one(metrics)

        shutil.rmtree(folder)
