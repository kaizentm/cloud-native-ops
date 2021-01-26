import os
import requests
import logging

class GitHubGitOps:


# curl -X POST -H "Authorization: token $TOKEN" \
#      -d '{"state":"success"}' \
#      https://api.github.com/repos/kaizentm/gitops-manifests/statuses/c0ca84a63e42797618313a5245a659c736f5ff81

    def __init__(self):
        self.org_url = os.getenv("AZDO_ORG_URL")  #https://api.github.com/repos/kaizentm
        self.gitops_repo_name = os.getenv("AZDO_GITOPS_REPO_NAME") #gitops-manifest
        # token is supposed to be stored in a secret without any transformations
        self.token = os.getenv("PAT")
        self.headers = {'Authorization': f'token {self.token}'}

    ### Convert Flux reasons to GitHub commit states
    ### https://docs.github.com/en/rest/reference/repos#create-a-commit-status
    def map_reason_to_github_state(self, reason):
        reason_state_map = {
            "ReconciliationSucceeded": "success",
            "ReconciliationFailed": "failure",
            "Progressing": "pending",
            "DependencyNotReady": "error",
            "PruneFailed": "failure",
            "ArtifactFailed": "failure",
            "BuildFailed": "failure",
            "HealthCheckFailed": "failure",
            "ValidationFailed": "failure"
        }
        return reason_state_map[reason]

    def map_reason_to_description(self, reason):
        reason_descrptn_map = {
            "ReconciliationSucceeded": "Reconcilation succeeded.",
            "ReconciliationFailed": "Reconcilation failed.",
            "Progressing": "Reconcilation underway.",
            "DependencyNotReady": "Dependency not ready.",
            "PruneFailed": "Pruning failed.",
            "ArtifactFailed": "Artifact download failed.",
            "BuildFailed": "Build failed.",
            "HealthCheckFailed": "A health check failed.",
            "ValidationFailed": "Manifests validation failed."
        }
        return reason_descrptn_map[reason]

    def update_commit_status(self, commitid, github_state, message):
        url = f'{self.org_url}/{self.gitops_repo_name}/statuses/{commitid}'

        data = {'state': github_state, 'description': message, 'context': 'Kustomization' }
        logging.info(f'Url {url}: Headers {self.headers}: Data {data}')
        response = requests.post(url=url, headers=self.headers, json=data)
        # Throw appropriate exception if request failed
        response.raise_for_status()

    # Update the statuses in Azure DevOps in the commit history view.
    def update_commit_statuses(self, event_data):
        revision = event_data['metadata']['revision']
        revisionArray = revision.split('/', 2)
        branch = revisionArray[0]
        commitid = revisionArray[1]
        logging.info(f'Commit {commitid}: Updating state data')
        reason_state = self.map_reason_to_github_state(event_data['reason'])
        reason_message = self.map_reason_to_description(event_data['reason'])
        self.update_commit_status(commitid, reason_state, reason_message)

        logging.info(f'Commit {commitid}: Updating state data')