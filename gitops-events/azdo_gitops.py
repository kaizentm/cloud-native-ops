import os
import requests
import json

# Temp storage in memory for a prototype. 
# To be changed. The connection between the PR and agentless task should be stored in the PR itself
pr_task_data = {}


class AzureDevOpsGitOps:


# curl -v -H "Authorization: Basic $B64_PAT" -H "Content-Type: application/json" \
#         -d '{"state": "succeeded", "description": "The changes have been succesfully applied", "targetUrl": "https://argodashboard.westus.cloudapp.azure.com/applications/az-vote-dev", "context": {"name": "Healthy", "genre": "Health"} }' \
#        "https://dev.azure.com/csedevops/GitOps/_apis/git/repositories/azure-vote-app-deployment/commits/0d46b0e0f75c17259063e28da83a3b1be738bb1d/statuses?api-version=6.0"

    def __init__(self):
        self.org_url = os.getenv("AZDO_ORG_URL")  #https://dev.azure.com/csedevops/GitOps
        self.token = os.getenv("PAT")
        self.headers = {'authorization': f'Basic {self.token}',
                        'Content-Type' : 'application/json'}

    def process_gitops_phase(self, gitops_phase_data):
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
            self.update_pr_task(state, commitid)

    def update_commit_status(self, commitid, state, health, message):
        url = self.org_url + f'/_apis/git/repositories/azure-vote-app-deployment/commits/{commitid}/statuses?api-version=6.0'
        callback_url = os.getenv("GITOPS_APP_URL") 
        data = {'state': state, 'description': message, 'targetUrl': callback_url, 'context': {'name': health, 'genre': 'Health'} }
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
        return pr_task_data[pr_num]

    def update_pr_task(self, state, commitid):
        pr_num = self.get_pr_num(commitid)
        if pr_num:
            pr_task = self.get_pr_task_data(pr_num)
            planurl = pr_task['planurl']
            projectid = pr_task['projectid']
            planid = pr_task['planid']
            url = f'{planurl}{projectid}/_apis/distributedtask/hubs/build/plans/{planid}/events?api-version=2.0-preview.1'
            data = {'name': "TaskCompleted", 'taskId': pr_task['taskid'], 'jobid': pr_task['jobid'], 'result': state }
            response = requests.post(url=url, headers=self.headers, json=data)
            print(response.content)
            assert response.status_code == 204