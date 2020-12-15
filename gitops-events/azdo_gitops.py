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
        assert response.status_code == 201

    def update_commit_statuses(self, commitid, phase, sync_status, health, message, resources):
        self.update_commit_status(commitid, 'Phase', self.map_phase_to_azdo_status(phase), phase + ": " + message)

        (health_summary, sync_summary) = self.get_deployment_status_summary(resources)

        self.update_commit_status(commitid, 'Sync', self.map_sync_status_to_azdo_status(sync_status), sync_summary)

        self.update_commit_status(commitid, 'Health', self.map_health_to_azdo_status(health), health_summary)
