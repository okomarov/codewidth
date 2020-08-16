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

if __name__ == '__main__':
    repos = github_client.get_repos_by_language(language='python')
    for repo in repos:
        name = repo.full_name
        if db_logic.check_exists({'name': name}):
            continue

        files = query_repository_logic.list_python_files_of_interest(repo)
        if len(files) < 1:
            continue
        folder = query_repository_logic.download_repo(
            repo, selected_files=[f.path for f in files])

        metrics = {'name': name, 'created_at': datetime.utcnow().isoformat()}
        print(metrics)
        file_metrics = code_analysis_logic.calculate_metrics(folder)
        metrics.update(code_analysis_logic.consolidate_repo_metrics(file_metrics))

        db_logic.insert_one(metrics)

        shutil.rmtree(folder)
