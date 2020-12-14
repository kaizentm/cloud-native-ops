import os
import requests


class AzureDevOpsGitOps:


# curl -v -H "Authorization: Basic $B64_PAT" -H "Content-Type: application/json" \
#         -d '{"state": "succeeded", "description": "The changes have been succesfully applied", "targetUrl": "https://argodashboard.westus.cloudapp.azure.com/applications/az-vote-dev", "context": {"name": "Healthy", "genre": "Health"} }' \
#        "https://dev.azure.com/csedevops/GitOps/_apis/git/repositories/azure-vote-app-deployment/commits/0d46b0e0f75c17259063e28da83a3b1be738bb1d/statuses?api-version=6.0"

    def __init__(self):
        self.org_url = os.getenv("AZDO_ORG_URL")  #https://dev.azure.com/csedevops/GitOps
        self.token = os.getenv("PAT")
        self.headers = {'authorization': f'Basic {self.token}',
                        'Content-Type' : 'application/json'}

    def process_gitops_phase(self, gitops_phase_data, pr_task_data):
        print(gitops_phase_data)
        commitid = gitops_phase_data['commitid']
        state = gitops_phase_data['state']
        health = gitops_phase_data['health']
        message = gitops_phase_data['message']
        if state=="Running" or health=="Progressing":
            state = "Pending"   
        if health=="Degraded":
            state = "Failed"             

        self.update_commit_status(commitid, state, health, message)

        if state == "Succeeded" or state == "Failed" or state == "Error":
            if state == "Error":
                state = "Failed"
            self.update_pr_task(state, pr_task_data)

    def update_commit_status(self, commitid, state, health, message):
        url = self.org_url + f'/_apis/git/repositories/azure-vote-app-deployment/commits/{commitid}/statuses?api-version=6.0'
        callback_url = os.getenv("GITOPS_APP_URL") 
        data = {'state': state, 'description': message, 'targetUrl': callback_url, 'context': {'name': health, 'genre': 'Health'} }
        response = requests.post(url=url, headers=self.headers, json=data)
        print(response.content)
        assert response.status_code == 201


    def update_pr_task(self, state, pr_task_data):
        planurl = pr_task_data['planurl']
        projectid = pr_task_data['projectid']
        planid = pr_task_data['planid']
        url = f'{planurl}{projectid}/_apis/distributedtask/hubs/build/plans/{planid}/events?api-version=2.0-preview.1'
        data = {'name': "TaskCompleted", 'taskId': pr_task_data['taskid'], 'jobid': pr_task_data['jobid'], 'result': state }
        response = requests.post(url=url, headers=self.headers, json=data)
        print(response.content)
        assert response.status_code == 204