import os
import logging
from operators.argo_gitops_operator import ArgoGitopsOperator
from operators.gitops_operator import GitopsOperatorInterface

FLUX_TYPE = "FLUX"
ARGOCD_TYPE = "ARGOCD"

class GitopsOperatorFactory:

    @staticmethod
    def new_gitops_operator() -> GitopsOperatorInterface:
        gitops_operator_type = os.getenv("GITOPS_OPERATOR_TYPE", FLUX_TYPE)

        if gitops_operator_type == FLUX_TYPE:
            # return FluxGitopsOperator()
            return ArgoGitopsOperator()
        elif gitops_operator_type == ARGOCD_TYPE:
            return ArgoGitopsOperator()
        else:
            raise NotImplementedError(f'The GitOps operator {gitops_operator_type} is not supported')
    


