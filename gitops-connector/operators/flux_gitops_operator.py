import logging
from operators.gitops_operator import GitopsOperatorInterface
from operators.git_commit_status import GitCommitStatus


class FluxGitopsOperator(GitopsOperatorInterface):

    def extract_commit_statuses(self, phase_data):
        commit_statuses = []

        commit_id = self.get_commit_id(phase_data)
        
        reason_state = phase_data['reason']
        reason_message = self._map_reason_to_description(reason_state)

        status = GitCommitStatus(commit_id = commit_id, status_name = 'Phase',
             state = reason_state, message = reason_message, callback_url=self.callback_url, gitops_operator='Flux')
        commit_statuses.append(status) 

        return commit_statuses

    def is_finished(self, phase_data):
        status = phase_data['reason']

        is_finished = status != 'Progressing'
        
        is_successful = status == 'ReconciliationSucceeded'

        return is_finished, is_successful

    def get_commit_id(self, phase_data) -> str:
        revision = phase_data['metadata']['revision']
        revisionArray = revision.split('/')
        commit_id = revisionArray[-1]
        return commit_id
    
    def is_supported_message(self, phase_data) -> bool:
        kind = phase_data['involvedObject']['kind']
        logging.debug(f'Kind: {kind}')
        return (kind == 'Kustomization')

    def _map_reason_to_description(self, reason):
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