import os
import requests
import json
from clients.azdo_client import AzdoClient
from repositories.git_repository import GitRepositoryInterface


PR_METADATA_KEY = "argocd-callback-task-id"

class AzdoGitRepository(GitRepositoryInterface):
    
    def __init__(self):
        self.gitops_repo_name = os.getenv("AZDO_GITOPS_REPO_NAME")
        self.azdo_client = AzdoClient()
        self.repository_api = f'{self.azdo_client.get_rest_api_url()}/_apis/git/repositories/{self.gitops_repo_name}'
        self.headers = self.azdo_client.get_rest_api_headers()
        

    def post_commit_status(self, commit_status):
        url = f'{self.repository_api}/commits/{commit_status.commit_id}/statuses?api-version=6.0'

        azdo_status = self._map_to_azdo_status(commit_status.state)
        data = {'state': azdo_status, 'description': commit_status.status_name + ": " + commit_status.message, \
                'targetUrl': commit_status.callback_url + "?noop=" + commit_status.status_name, \
                'context': {'name': commit_status.status_name, 'genre': commit_status.gitops_operator} }
        response = requests.post(url=url, headers=self.headers, json=data)

        # Throw appropriate exception if request failed
        response.raise_for_status()

    def get_pr_metadata(self, pr_num):
        # https://docs.microsoft.com/en-us/rest/api/azure/devops/git/pull%20request%20properties/list?view=azure-devops-rest-6.0
        url = f'{self.repository_api}/pullRequests/{pr_num}/properties?api-version=6.0-preview'

        response = requests.get(url=url, headers=self.headers)
        # Throw appropriate exception if request failed
        response.raise_for_status()

        # Navigate the properties response structure
        result = response.json()
        if (result['count'] > 0):
            properties = result['value']
            entry = properties.get(PR_METADATA_KEY)
            if entry:
                # At this point, we have the original JSON string we stored.
                return json.loads(entry['$value'])
        return None
    

    
    def _map_to_azdo_status(self, status):
        status_map = {
            "Succeeded": "succeeded",
            "Failed": "failed",
            "Error": "error",
            "Inconclusive": "pending",
            "Running": "pending",
            "OutOfSync": "pending",
            "Synced": "succeeded",
            "Unknown": "notApplicable",
            "Progressing": "pending",
            "Degraded": "error",
            "Healthy": "succeeded",
            "Missing": "failed",
            "Suspended": "error",
            "ReconciliationSucceeded": "succeeded",
            "ReconciliationFailed": "failed",
            "Progressing": "pending",
            "DependencyNotReady": "error",
            "PruneFailed": "failed",
            "ArtifactFailed": "failed",
            "BuildFailed": "failed",
            "HealthCheckFailed": "failed",
            "ValidationFailed": "failed"
        }
        return status_map[status]


    def get_pr_num(self, commit_id) -> str:
        url = f'{self.repository_api}/commits/{commit_id}?api-version=6.0'

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

