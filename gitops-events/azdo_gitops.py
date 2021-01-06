import os
import requests
import json
import base64

# Temp storage in memory for a prototype. 
# To be changed. The connection between the PR and agentless task should be stored in the PR itself
pr_task_data = {}


class AzureDevOpsGitOps:


# curl -v -H "Authorization: Basic $B64_PAT" -H "Content-Type: application/json" \
#         -d '{"state": "succeeded", "description": "The changes have been succesfully applied", "targetUrl": "https://argodashboard.westus.cloudapp.azure.com/applications/az-vote-dev", "context": {"name": "Healthy", "genre": "Health"} }' \
#        "https://dev.azure.com/csedevops/GitOps/_apis/git/repositories/azure-vote-app-deployment/commits/0d46b0e0f75c17259063e28da83a3b1be738bb1d/statuses?api-version=6.0"

    def __init__(self):
        self.org_url = os.getenv("AZDO_ORG_URL")  #https://dev.azure.com/csedevops/GitOps
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

    def process_gitops_phase(self, gitops_phase_data):
        print(gitops_phase_data)
        commitid = gitops_phase_data['commitid']
        phase = gitops_phase_data['phase']
        sync_status = gitops_phase_data['sync_status']
        health = gitops_phase_data['health']
        message = gitops_phase_data['message']
        resources = gitops_phase_data['resources']
        self.update_commit_statuses(commitid, phase, sync_status, health, message, resources)

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
        url = self.org_url + f'/_apis/git/repositories/azure-vote-app-deployment/commits/{commitid}/statuses?api-version=6.0'

        callback_url = os.getenv("GITOPS_APP_URL")
        data = {'state': azdo_state, 'description': status_name + ": " + message, 'targetUrl': callback_url + "?noop=" + status_name, 'context': {'name': status_name, 'genre': 'ArgoCD'} }
        response = requests.post(url=url, headers=self.headers, json=data)
        print(response.content)
        print(response.status_code)
        assert response.status_code == 201

    def get_pr_num(self, commitid):
        url = self.org_url + f'/_apis/git/repositories/azure-vote-app-deployment/commits/{commitid}?api-version=6.0'
        response = requests.get(url=url, headers=self.headers)
        commit = json.loads(response.content)                
        comment = commit['comment']
        MERGED_PR="Merged PR "
        pr_num = None
        if MERGED_PR in comment:
            pr_num = comment[comment.index(MERGED_PR) + len(MERGED_PR) : comment.index(":")]
        return pr_num
    
    # These too functions update_pr_task_data and get_pr_task_data will be changed 
    # when we change how pr_num<->taskid connection is stored
    def update_pr_task_data(self, payload):
        global pr_task_data
        pr_task_data[payload['pr_num']] = payload

    def get_pr_task_data(self, pr_num):        
        if pr_num in pr_task_data:
            return pr_task_data[pr_num]
        else:
            return None

    def update_pr_task(self, state, pr_num):
        pr_task = self.get_pr_task_data(pr_num)
        if pr_task:
            planurl = pr_task['planurl']
            projectid = pr_task['projectid']
            planid = pr_task['planid']
            url = f'{planurl}{projectid}/_apis/distributedtask/hubs/build/plans/{planid}/events?api-version=2.0-preview.1'
            data = {'name': "TaskCompleted", 'taskId': pr_task['taskid'], 'jobid': pr_task['jobid'], 'result': state }
            response = requests.post(url=url, headers=self.headers, json=data)
            print(response.content)
        else:
            print(f'There is no data for pr [{pr_num}]')

    def update_commit_statuses(self, commitid, phase, sync_status, health, message, resources):
        phase_status = self.map_phase_to_azdo_status(phase)
        self.update_commit_status(commitid, 'Phase', phase_status, phase + ": " + message)

        (health_summary, sync_summary) = self.get_deployment_status_summary(resources)

        self.update_commit_status(commitid, 'Sync', self.map_sync_status_to_azdo_status(sync_status), sync_summary)

        health_status = self.map_health_to_azdo_status(health)
        self.update_commit_status(commitid, 'Health', health_status, health_summary)
                
        if phase_status != 'pending' and health_status != 'pending':  
            if phase_status == 'succeeded' and health_status == 'succeeded':
               state = 'succeeded'
            else:
                state = 'failed'
            pr_num = self.get_pr_num(commitid)
            if pr_num:
                self.update_pr_task(state, pr_num)

    def get_pull_request(self, pr_num):
        url = self.org_url + f'/_apis/git/pullrequests/{pr_num}?api-version=6.1-preview.1'
        response = requests.get(url=url, headers=self.headers)
        pr = json.loads(response.content)                
        return pr
    
    
    def process_pr_status_updated(self, payload):
        pr_num = payload['resource']['pullRequestId']
        print(f'pr_num:[{pr_num}]')
        pr = self.get_pull_request(pr_num)
        pr_status = pr['status']
        if (pr_status == 'abandoned'):
            self.update_pr_task('failed', str(pr_num))


