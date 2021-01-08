import base64
import json
import logging
import os
import requests

# We need to store the agentless task ID that is waiting for a PR to complete.
# The data is stored remotely in the PR metadata, and we also cache it locally.
PR_METADATA_KEY = "argocd-callback-task-id"
pr_task_data_cache = {}


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
        pr_task_data_cache[payload['pr_num']] = payload

        self.add_pr_metadata(payload['pr_num'], PR_METADATA_KEY, payload)

    def get_pr_task_data(self, pr_num):
        if pr_num in pr_task_data_cache:
            logging.info(f'PR {pr_num}: Metadata read cache hit')
            # We only expect to have one callback, so remove the cache entry.
            return pr_task_data_cache.pop(pr_num)

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
    def update_pr_task(self, state, pr_num):
        logging.info(f'PR {pr_num}: Rollout {state}, attempting task completion callback...')
        pr_task = self.get_pr_task_data(pr_num)
        if not pr_task:
            logging.error(f'PR {pr_num} has no metadata! Cannot complete task callback.')
            return

        # The build task may have been cancelled, timed out, etc.
        # Working with the plan in this state can cause 500 errors.
        # Finish gracefully so ArgoCD doesn't keep calling us.
        if self.plan_already_completed(pr_task):
            return

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
        pr = json.loads(response.content)
        return pr

    def ensure_pr_alive(self, pr_num):
        pr = self.get_pull_request(pr_num)
        pr_status = pr['status']
        if (pr_status == 'abandoned'):
            self.update_pr_task('failed', str(pr_num))
            return False
        return True

    def process_pr_status_updated(self, payload):
        pr_num = payload['resource']['pullRequestId']
        self.ensure_pr_alive(pr_num)

    def process_update_pr_task(self, payload):
        # Before checking if we should add PR data, make sure we're in a good state
        if not self.ensure_pr_alive(payload["pr_num"]):
            return

        self.add_pr_task_data(payload)