from operators.gitops_operator import GitopsOperatorInterface
from operators.git_commit_status import GitCommitStatus

class FluxGitopsOperator(GitopsOperatorInterface):

    def extract_commit_statuses(self, phase_data):
        commit_statuses = []

        commit_id = self.get_commit_id(phase_data)
        
        reason_state = phase_data['reason']
        reason_message = phase_data['reason']

        status = GitCommitStatus(commit_id = commit_id, status_name = 'Phase',
             state = reason_state, message = reason_message)
        commit_statuses.append(status) 

        return commit_statuses

    def is_finished(self, phase_data):
        status = phase_data['reason']

        is_finished = status != 'Progressing'
        
        is_successful = status == 'ReconciliationSucceeded'

        return is_finished, is_successful

    def get_commit_id(self, c) -> str:
        revision = phase_data['metadata']['revision']
        revisionArray = revision.split('/', 2)
        commit_id = revisionArray[1]
        return commit_id

