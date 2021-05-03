from collections import defaultdict
import logging
from operators.gitops_operator import GitopsOperatorInterface
from operators.git_commit_status import GitCommitStatus


class FluxGitopsOperator(GitopsOperatorInterface):

    def extract_commit_statuses(self, phase_data):
        commit_statuses = []

        commit_id = self.get_commit_id(phase_data)

        reason_state = phase_data['reason']
        reason_message = self._map_reason_to_description(reason_state, phase_data['message'])
        kind = self._get_message_kind(phase_data)


        # For Kustomization we have more detailed data to parse in addition to status.
        if self._get_message_kind(phase_data) == "Kustomization":
            progression_summary = self._parse_kustomization_progression_summary(phase_data)
            if progression_summary:
                for (resource_name, status_msg) in progression_summary.items():
                    status = GitCommitStatus(
                        commit_id = commit_id,
                        status_name = resource_name,
                        # As far as the Kustomize controller is concerned, these are finished
                        # before reconciliation starts. We don't want this to affect the overall
                        # status, so map to the relevant N/A status in the Git repo provider.
                        state = "NotApplicable",
                        message = status_msg,
                        callback_url=self.callback_url,
                        gitops_operator='Flux',
                        genre=kind)
                    commit_statuses.append(status)

        # Generic status message regardless of kind.
        status = GitCommitStatus(
            commit_id = commit_id,
            status_name = 'Status',
            state = reason_state,
            message = reason_message,
            callback_url=self.callback_url,
            gitops_operator='Flux',
            genre=kind)
        commit_statuses.append(status)

        return commit_statuses

    def is_finished(self, phase_data):
        status = phase_data['reason']

        is_finished = status != 'Progressing'

        is_successful = status == 'ReconciliationSucceeded'

        return is_finished, is_successful

    def get_commit_id(self, phase_data) -> str:
        if self._get_message_kind(phase_data) == "Kustomization":
            revision = phase_data['metadata']['revision']
        elif self._get_message_kind(phase_data) == 'GitRepository':
            # 'Fetched revision: user/blah/githash'
            revision = phase_data['message']
        revisionArray = revision.split('/')
        commit_id = revisionArray[-1]

        return commit_id

    def is_supported_message(self, phase_data) -> bool:
        kind = self._get_message_kind(phase_data)
        logging.debug(f'Kind: {kind}')

        return (kind == 'Kustomization' or kind == 'GitRepository')

    def _get_message_kind(self, phase_data) -> str:
        return phase_data['involvedObject']['kind']

    def _map_reason_to_description(self, reason, original_message):
        # Explicitly handle all statuses so we make sure we don't silently miss any.
        reason_description_map = {
            "ReconciliationSucceeded": original_message,
            "ReconciliationFailed": original_message,
            "Progressing": "Reconcilation underway.",
            "DependencyNotReady": original_message,
            "PruneFailed": original_message,
            "ArtifactFailed": original_message,
            "BuildFailed": original_message,
            "HealthCheckFailed": original_message,
            "ValidationFailed": "Manifests validation failed.",
            "info": original_message,
            "error": original_message
        }
        return reason_description_map[reason]

    # Build and return an array of progression summaries.
    # For example, ["service: 6 configured"]
    def _parse_kustomization_progression_summary(self, phase_data):
        if phase_data['reason'] != "Progressing":
            return []

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
        status_arr = {}
        for (resource_name, statuses) in status_map.items():
            ## service:
            summary = ""
            first = True
            for (status_name, status_count) in statuses.items():
                if not first:
                    summary += ", "
                    first = False
                # E.g. "5 configured"
                summary += f'{status_count} {status_name}'
            status_arr[resource_name] = summary

        if warning_count > 0:
            status_arr['warnings'] = f'Warnings: {warning_count}'

        return status_arr
