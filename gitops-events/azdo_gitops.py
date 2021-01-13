import base64
from datetime import datetime, timedelta
import dateutil.parser
import json
import logging
import os
import requests
from threading import Lock

# We need to store the agentless task ID that is waiting for a PR to complete.
# The data is stored remotely in the PR metadata, and we also cache it locally.
PR_METADATA_KEY = "argocd-callback-task-id"
pr_task_data_cache = {}
# A lock is needed since we have non-atomic operations, i.e. if-read-then-write.
pr_cache_lock = Lock()

# Callback task timeout in minutes. PRs abandoned before this time will not be processed.
MAX_TASK_TIMEOUT = 72 * 60
TASK_CUTOFF_DURATION = timedelta(minutes=MAX_TASK_TIMEOUT)


class AzureDevOpsGitOps:


# curl -v -H "Authorization: Basic $B64_PAT" -H "Content-Type: application/json" \
#         -d '{"state": "succeeded", "description": "The changes have been succesfully applied", "targetUrl": "https://argodashboard.westus.cloudapp.azure.com/applications/az-vote-dev", "context": {"name": "Healthy", "genre": "Health"} }' \
#        "https://dev.azure.com/csedevops/GitOps/_apis/git/repositories/azure-vote-app-deployment/commits/0d46b0e0f75c17259063e28da83a3b1be738bb1d/statuses?api-version=6.0"

    def __init__(self):
        self.org_url = os.getenv("AZDO_ORG_URL")  #https://dev.azure.com/csedevops/GitOps
        self.gitops_repo_name = os.getenv("AZDO_GITOPS_REPO_NAME") #
        # token is supposed to be stored in a secret without any transformations
        self.token = base64.b64encode(f':{os.getenv("PAT")}'.encode("ascii")).decode("ascii")
        self.headers = {'authorization': f'Basic {self.token}',
                        'Content-Type' : 'application/json'}

    ### Convert ArgoCD states to AzDO commit states
    ### https://docs.microsoft.com/en-us/rest/api/azure/devops/git/statuses/create?view=azure-devops-rest-6.0#gitstatusstate
    def map_phase_to_azdo_status(self, phase):
        phase_map = {
            "Succeeded": "succeeded",
            "Failed": "failed",
            "Error": "error",
            "Inconclusive": "pending",
            "Running": "pending"
        }
        return phase_map[phase]

    def map_sync_status_to_azdo_status(self, sync_status):
        sync_map = {
            "OutOfSync": "pending",
            "Synced": "succeeded",
            "Unknown": "notApplicable",
        }
        return sync_map[sync_status]

    def map_health_to_azdo_status(self, health):
        health_map = {
            "Progressing": "pending",
            "Degraded": "error",
            "Healthy": "succeeded",
            "Missing": "failed",
            "Suspended": "error",
            "Unknown": "notApplicable",
        }
        return health_map[health]

    def get_deployment_status_summary(self, resources):
        total = len(resources)
        health_count = {}
        sync_count = {}

        for resource in resources:
            if 'health' in resource: #  not every resource has health key
                health = resource['health']['status']
                health_count[health] = health_count.get(health, 0) + 1
            sync_count[resource['status']] = sync_count.get(resource['status'], 0) + 1

        def summarize(status_count):
            status_summary = ""
            first = True
            for status, count in status_count.items():
                if first is not True:
                    status_summary += ", "
                else:
                    first = False
                status_summary += "%d/%d %s" % (count, total, status)
            return status_summary

        return (summarize(health_count), summarize(sync_count))

    def update_commit_status(self, commitid, status_name, azdo_state, message):
        url = f'{self.org_url}/_apis/git/repositories/{self.gitops_repo_name}/commits/{commitid}/statuses?api-version=6.0'

        callback_url = os.getenv("GITOPS_APP_URL")
        data = {'state': azdo_state, 'description': status_name + ": " + message, 'targetUrl': callback_url + "?noop=" + status_name, 'context': {'name': status_name, 'genre': 'ArgoCD'} }
        response = requests.post(url=url, headers=self.headers, json=data)
        # Throw appropriate exception if request failed
        response.raise_for_status()

    def get_pr_num(self, commitid):
        url = f'{self.org_url}/_apis/git/repositories/{self.gitops_repo_name}/commits/{commitid}?api-version=6.0'

        response = requests.get(url=url, headers=self.headers)
        # Throw appropriate exception if request failed
        response.raise_for_status()

        commit = response.json()
        comment = commit['comment']
        MERGED_PR="Merged PR "
        pr_num = None
        if MERGED_PR in comment:
            pr_num = comment[comment.index(MERGED_PR) + len(MERGED_PR) : comment.index(":")]
        return pr_num

    # Returns None if no property was found.
    def get_pr_metadata(self, pr_num, key):
        # https://docs.microsoft.com/en-us/rest/api/azure/devops/git/pull%20request%20properties/list?view=azure-devops-rest-6.0
        url = f'{self.org_url}/_apis/git/repositories/{self.gitops_repo_name}/pullRequests/{pr_num}/properties?api-version=6.0-preview'

        response = requests.get(url=url, headers=self.headers)
        # Throw appropriate exception if request failed
        response.raise_for_status()

        # Navigate the properties response structure
        result = response.json()
        if (result['count'] > 0):
            properties = result['value']
            entry = properties.get(key)
            if entry:
                # At this point, we have the original JSON string we stored.
                return json.loads(entry['$value'])

        return None

    ### Will fail if metadata already exists for the given path.
    def add_pr_metadata(self, pr_num, key, value):
        # https://docs.microsoft.com/en-us/rest/api/azure/devops/git/pull%20request%20properties/update?view=azure-devops-rest-6.0
        url = f'{self.org_url}/_apis/git/repositories/{self.gitops_repo_name}/pullRequests/{pr_num}/properties?api-version=6.0-preview'
        value_str = json.dumps(value)
        escaped_str = json.dumps(value_str)

        # Key must start with '/', even though it won't be returned as a path in GET
        payload = f"""
            [
                {{
                    "op": "add",
                    "path": "/{key}",
                    "from": null,
                    "value": {escaped_str}
                }}
            ]
        """

        headers_patch = self.headers.copy()
        headers_patch['Content-Type'] = "application/json-patch+json"

        response = requests.patch(url=url, headers=headers_patch, data=payload)
        # Throw appropriate exception if request failed
        response.raise_for_status()

    # Read/write for PR->TaskID value in AzDO and local cache.
    def add_pr_task_data(self, payload):
        logging.info(f'PR {payload["pr_num"]}: Storing and caching metadata for task {payload["taskid"]}')
        with pr_cache_lock:
            pr_task_data_cache[payload['pr_num']] = payload

        self.add_pr_metadata(payload['pr_num'], PR_METADATA_KEY, payload)

    # is_alive: Metadata cache misses are OK if the PR is abandoned.
    def get_pr_task_data(self, pr_num, is_alive=True):
        # Lock the cache due to temporal store.
        with pr_cache_lock:
            if pr_num in pr_task_data_cache:
                logging.info(f'PR {pr_num}: Metadata read cache hit')
                # We only expect to have one callback, so remove the cache entry.
                return pr_task_data_cache.pop(pr_num)

        if is_alive:
            logging.warning(f'PR {pr_num}: Metadata cache miss')
        return self.get_pr_metadata(pr_num, PR_METADATA_KEY)

    # Given a PR task, check if it's parent plan has already completed.
    # Note: Completed does not necessarily mean it succeeded.
    def plan_already_completed(self, pr_task):
        planurl = pr_task['planurl']
        projectid = pr_task['projectid']
        planid = pr_task['planid']
        url = f'{planurl}{projectid}/_apis/distributedtask/hubs/build/plans/{planid}'

        response = requests.get(url=url, headers=self.headers)
        # Throw appropriate exception if request failed
        response.raise_for_status()

        plan_info = response.json()
        return plan_info['state'] == 'completed'

    # Update the Azure Pipeline task waiting for the PR to complete.
    # is_alive: If true, the PR is active and absence of task data is an error.
    def update_pr_task(self, state, pr_num, is_alive=True):
        pr_task = self.get_pr_task_data(pr_num, is_alive)
        if not pr_task:
            if is_alive:
                logging.error(f'PR {pr_num} has no metadata! Cannot complete task callback.')
            return False
        logging.info(f'PR {pr_num}: Rollout {state}, attempting task completion callback...')

        # The build task may have been cancelled, timed out, etc.
        # Working with the plan in this state can cause 500 errors.
        # Finish gracefully so ArgoCD doesn't keep calling us.
        if self.plan_already_completed(pr_task):
            return False

        planurl = pr_task['planurl']
        projectid = pr_task['projectid']
        planid = pr_task['planid']
        url = f'{planurl}{projectid}/_apis/distributedtask/hubs/build/plans/{planid}/events?api-version=2.0-preview.1'
        data = {
            'name': "TaskCompleted",
            'taskId': pr_task['taskid'],
            'jobid': pr_task['jobid'],
            'result': state
        }
        response = requests.post(url=url, headers=self.headers, json=data)
        # Throw appropriate exception if request failed
        response.raise_for_status()

        logging.info(f'PR {pr_num}: Successfully completed task {pr_task["taskid"]}')
        return True

    # Update the statuses in Azure DevOps in the commit history view.
    def update_commit_statuses(self, phase_data):
        logging.info(f'Commit {phase_data["commitid"]}: Updating phase data')
        phase_status = self.map_phase_to_azdo_status(phase_data['phase'])
        self.update_commit_status(phase_data['commitid'], 'Phase', phase_status, phase_data['phase'] + ": " + phase_data['message'])

        (health_summary, sync_summary) = self.get_deployment_status_summary(phase_data['resources'])

        self.update_commit_status(phase_data['commitid'], 'Sync', self.map_sync_status_to_azdo_status(phase_data['sync_status']), sync_summary)

        health_status = self.map_health_to_azdo_status(phase_data['health'])
        self.update_commit_status(phase_data['commitid'], 'Health', health_status, health_summary)

        logging.info(f'Commit {phase_data["commitid"]}: Updating phase data')

        if phase_status != 'pending' and health_status != 'pending':
            if phase_status == 'succeeded' and health_status == 'succeeded':
                state = 'succeeded'
            else:
                state = 'failed'
            pr_num = self.get_pr_num(phase_data['commitid'])
            if pr_num:
                self.update_pr_task(state, pr_num)

    def get_pull_request(self, pr_num):
        url = f'{self.org_url}/_apis/git/pullrequests/{pr_num}?api-version=6.1-preview.1'
        response = requests.get(url=url, headers=self.headers)
        # Throw appropriate exception if request failed
        response.raise_for_status()
        pr = json.loads(response.content)
        return pr

    # Returns False if the PR is no longer alive and we notified the task.
    def update_abandoned_pr(self, pr_num, pr_data=None):
        # Skip pulling the PR data if we already have it.
        if pr_data:
            pr = pr_data
        else:
            pr = self.get_pull_request(pr_num)

        pr_status = pr['status']
        if (pr_status == 'abandoned'):
            # update_pr_task returns True if the task was updated.
            return not self.update_pr_task('failed', str(pr_num), is_alive=False)
        return True

    # Returns an array of PR dictionaries with an optional status filter
    # pr_status values: https://docs.microsoft.com/en-us/rest/api/azure/devops/git/pull%20requests/get%20pull%20requests?view=azure-devops-rest-6.0#pullrequeststatus
    def get_prs(self, pr_status): 
        pr_status_param = ''
        if pr_status:
            pr_status_param = f'searchCriteria.status={pr_status}&'
        url = f'{self.org_url}/_apis/git/repositories/{self.gitops_repo_name}/pullRequests?{pr_status_param}api-version=6.0'
        response = requests.get(url=url, headers=self.headers)
        # Throw appropriate exception if request failed
        response.raise_for_status()

        pr_response = json.loads(response.content)
        if pr_response['count'] == 0:
            return None

        return pr_response['value']

    # Returns True if the PR completed within the last TASK_CUTOFF_DURATION.
    def should_update_abandoned_pr(self, pr_data):
        closed_date = pr_data.get('closedDate')
        if not closed_date:
            return True

        # Azure DevOps returns a ISO 8601 formatted datetime string.
        closed_datetime = dateutil.parser.isoparse(closed_date)

        # Azure DevOps returns a timezone, so make now() relative to that.
        now = datetime.now(closed_datetime.tzinfo)

        return now - TASK_CUTOFF_DURATION <= closed_datetime

    # Find abandoned PRs and notify any associated tasks.
    def notify_abandoned_pr_tasks(self):
        update_count = 0
        prs = self.get_prs('abandoned')

        for pr in prs:
            if not self.should_update_abandoned_pr(pr):
                continue

            pr_num = pr['pullRequestId']
            if not self.update_abandoned_pr(pr_num, pr_data=pr):
                update_count += 1
                logging.debug(f'Updated abandoned PR {pr_num}')

        if update_count > 0:
            logging.info(f'Processed {update_count} abandoned PRs via query')

    def process_pr_status_updated(self, payload):
        pr_num = payload['resource']['pullRequestId']
        self.update_abandoned_pr(pr_num)

    def process_update_pr_task(self, payload):
        # Before checking if we should add PR data, make sure it's not abandoned.
        # If it was, we will trigger the callback without adding the task data.
        if self.update_abandoned_pr(payload["pr_num"]):
            return

        self.add_pr_task_data(payload)
