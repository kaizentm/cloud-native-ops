from flask import Flask, request
from azdo_gitops import AzureDevOpsGitOps
import logging

logging.basicConfig(level=logging.INFO)

application = Flask(__name__)

azdo_gitops = AzureDevOpsGitOps()

@application.route("/gitopsphase/", methods=['POST'])
def gitopsphase():
    payload = request.get_json()

    logging.debug(f'GitOps phase: {payload}')

    azdo_gitops.update_commit_statuses(payload)

    return f'GitOps phase: {payload}', 200

@application.route("/update-pr-task", methods=['POST'])
def update_pr_task():
    payload = request.get_json()

    logging.debug(f'update-pr-task: {payload}')

    azdo_gitops.process_update_pr_task(payload)

    return f'update-pr-task: {payload}', 200

@application.route("/pr-status-updated", methods=['POST'])
def pr_status_updated():
    payload = request.get_json()

    logging.debug(f'pr_status_updated: {payload}')

    azdo_gitops.process_pr_status_updated(payload)

    return f'pr_status_updated: {payload}', 200

# Add an azdo webhook listener to Invoke argo cd sync on push

if __name__ == "__main__":
    application.run(host='0.0.0.0')