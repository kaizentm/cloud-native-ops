from flask import Flask, request
from github_gitops import GitHubGitOps
import logging


logging.basicConfig(level=logging.INFO)

application = Flask(__name__)

github_gitops = GitHubGitOps()

@application.route("/", methods=['POST'])
def commitstatus():
    payload = request.get_json()

    logging.debug(f'GitOps phase: {payload}')

    github_gitops.update_commit_statuses(payload)

    return f'GitHub state: {payload}', 200

if __name__ == "__main__":
    application.run(host='0.0.0.0')