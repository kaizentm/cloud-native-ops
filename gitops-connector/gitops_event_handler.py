from flask import Flask, request
import logging
from timeloop import Timeloop
from datetime import timedelta
import atexit
import time
from gitops_connector import GitopsConnector

# Time in seconds between background PR cleanup jobs
PR_CLEANUP_INTERVAL = 1 * 30
DISABLE_POLLING_PR_TASK = False

logging.basicConfig(level=logging.DEBUG)

application = Flask(__name__)

gitops_connector = GitopsConnector()

@application.route("/gitopsphase", methods=['POST'])
def gitopsphase():
    # Use per process timer to stash the time we got the request
    reqtime = time.monotonic_ns()

    payload = request.get_json()

    logging.debug(f'GitOps phase: {payload}')

    gitops_connector.process_gitops_phase(payload, reqtime)

    return f'GitOps phase: {payload}', 200

# Periodic PR cleanup task
cleanup_task = Timeloop()
@cleanup_task.job(interval=timedelta(seconds=PR_CLEANUP_INTERVAL))
def pr_polling_thread_worker():
    logging.info("Starting periodic PR cleanup")
    gitops_connector.notify_abandoned_pr_tasks()
    logging.info(f'Finished PR cleanup, sleeping for {PR_CLEANUP_INTERVAL} seconds...')

# Git status queue drain task
queue_task = Timeloop()
@queue_task.job(interval=timedelta(seconds=10))
def commit_status_thread_worker():
    logging.info("Starting periodic commit status queue drain")
    gitops_connector.drain_commit_status_queue()
    logging.info(f'Finished commit statuses, sleeping for {10} seconds...')

def interrupt():
    if not DISABLE_POLLING_PR_TASK:
        cleanup_task.stop()
        queue_task.stop()


if not DISABLE_POLLING_PR_TASK:
    cleanup_task.start()
    queue_task.start()
    atexit.register(interrupt)

if __name__ == "__main__":
    application.run(host='0.0.0.0')