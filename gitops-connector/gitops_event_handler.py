from flask import Flask, request
from azdo_gitops import AzureDevOpsGitOps
import logging
from timeloop import Timeloop
from datetime import timedelta
import atexit
from gitops_connector import GitopsConnector

# Time in seconds between background PR cleanup jobs
PR_CLEANUP_INTERVAL = 1 * 60
DISABLE_POLLING_PR_TASK = False

logging.basicConfig(level=logging.INFO)

application = Flask(__name__)

azdo_gitops = AzureDevOpsGitOps()

gitops_connector = GitopsConnector()

# Periodic PR cleanup task
cleanup_task = Timeloop()
@cleanup_task.job(interval=timedelta(seconds=PR_CLEANUP_INTERVAL))
def pr_polling_thread_worker():
    logging.info("Starting periodic PR cleanup")
    azdo_gitops.notify_abandoned_pr_tasks()
    logging.info(f'Finished PR cleanup, sleeping for {PR_CLEANUP_INTERVAL} seconds...')


@application.route("/gitopsphase", methods=['POST'])
def gitopsphase():
    payload = request.get_json()

    logging.debug(f'GitOps phase: {payload}')

    gitops_connector.process_gitops_phase(payload)

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

def interrupt():
    if not DISABLE_POLLING_PR_TASK:
        cleanup_task.stop()


# Add an azdo webhook listener to Invoke argo cd sync on push

if not DISABLE_POLLING_PR_TASK:
    cleanup_task.start()
    atexit.register(interrupt)

if __name__ == "__main__":
    application.run(host='0.0.0.0')