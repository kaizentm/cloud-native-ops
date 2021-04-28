from collections import defaultdict
import logging
from operators.gitops_operator import GitopsOperatorInterface
from operators.git_commit_status import GitCommitStatus


class FluxGitopsOperator(GitopsOperatorInterface):

    def extract_commit_statuses(self, phase_data):
        commit_statuses = []

        commit_id = self.get_commit_id(phase_data)

        reason_state = phase_data['reason']
        reason_message = self._map_reason_to_description(reason_state)
        kind = self._get_message_kind(phase_data)

        status = GitCommitStatus(commit_id = commit_id, status_name = kind,
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
        kind = self._get_message_kind(phase_data)
        logging.debug(f'Kind: {kind}')
        return (kind == 'Kustomization')

    def _get_message_kind(self, phase_data) -> str:
        return phase_data['involvedObject']['kind']

    def _map_reason_to_description(self, reason):
        reason_description_map = {
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
        return reason_description_map[reason]

    # Build and return an array of progression summaries.
    # For example, ["service: 6 configured"]
    def _parse_kustomization_progression_summary(self, phase_data):
        if phase_data != "Progressing":
            raise RuntimeError("Expected progressing state for parsing")

        # The message contains kubectl output of newline separated
        # resources and states. May contain a trailing newline.
        raw_message = phase_data['message']
        entries = raw_message.rstrip().split("\n")

        if not entries or len(entries) == 0:
            return

        # Iterate on the entries and build our map.
        # Raw entry example:
        #   deployment.apps/abc configured
        #   deployment.apps/def configured
        status_map = defaultdict(lambda: defaultdict(int))
        warning_count = 0
        for entry in entries:
            # Split into resource and status
            if entry.startswith("Warning"):
                warning_count += 1
                continue

            entry_tuple = entry.split(" ")
            if len(entry_tuple) != 2:
                raise RuntimeError("Parsing error")
            (resource, status) = entry_tuple

            # Disregard the resource name
            (resource_type, _, _) = resource.partition("/")
            status_map[resource_type][status] += 1

        # Build the status string array
        status_arr = []
        for (resource_name, statuses) in status_map.items():
            ## service:
            summary = resource_name + ": "
            first = True
            for (status_name, status_count) in statuses.items():
                if not first:
                    summary += ", "
                    first = False
                # E.g. "5 configured"
                summary += f'{status_count} {status_name}'
            status_arr.append(summary)

        if warning_count > 0:
            status_arr.append(f'Warnings: {warning_count}')

        return status_arr
