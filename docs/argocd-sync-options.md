# ArgoCD Sync Operations Options:  

ArgoCD apps supports both manual and automatic sync options. If a sync policy is set to auto Argo CD will poll for any changes on the configured repositories and automatically apply any changes made to repositories.

However, there might be good number of scenarios where team would set sync policy to manually and explicitly call synchronization.

Performing Sync operation from Azure DevOps: 

**Option 1: Azure Devops Web Hooks**

    Create [Azure DevOps Web hook](https://docs.microsoft.com/en-us/azure/devops/service-hooks/services/webhooks?view=azure-devops) to trigger Argo CD Sync by configuring action that calls sync API e.g https://{dns_name}/api/v1/applications/{app_name}/sync 

   Pros:
   1. No build agent required to invoke sync.Save build time  especially in long running sync operations that consist lager number of manifests.  
   1. Webhook can be enabled and disabled from Azure DevOps without code change.
   
   Cons:
   1. From observability aspect its inconvenient to find out find out failed hooks and lineage
   1. Sync failure or success is not visually represented in web hook.

**Option 2: Azure Devops Pipeline**

   Synchronization can be invoked from Azure Pipelines from both agent and agent less job. 

   To invoke sync from agent based job both ArgoCD CLI and REST api can be used. However, if there are any post-sync operations like smoke-test to perform in the same pipeline. Lot of build agent time might be occupied waiting for sync operation to complete and separate pipeline should be used perform post sync operation. This pipeline can be triggered using ArgoCD post-sync resource hooks.  
   
   To invoke sync from agentless job use [Rest Api Task](https://docs.microsoft.com/en-us/azure/devops/pipelines/tasks/utility/http-rest-api?view=azure-devops) to call sync API e.g https://{dns_name}/api/v1/applications/{app_name}/sync and update call back details to app info. Further you can use ArgoCD post-sync resource hooks to signal the completion either success/failure of sync to the Azure pipelines over the callback url.

  Pros:
   1. No build agent required to invoke sync. Saves build time  especially in long running sync operations that consist lager number of manifests.
   1. Sync success or failure is reported back to Azure pipelines.
   
   Cons:
   1. Argo CD REST API needs to be exposed over HTTPS with signed TLS from trusted authority.

   **Bug Alert** : Current Sync API has a [bug](https://github.com/argoproj/argo-cd/issues/4954) that does not update app info.   


## [ArgoCD Resource Hooks](https://argoproj.github.io/argo-cd/user-guide/resource_hooks/) 

Synchronization can be configured using resource hooks. Hooks are ways to run scripts before, during, and after a Sync operation. Hooks can also be run if a Sync operation fails at any point. Some use cases for hooks are:

- Using a **PreSync** hook to perform a database schema migration before deploying a new version of the app.
- Using a **Sync hook** to orchestrate a complex deployment requiring more sophistication than the Kubernetes rolling update strategy.
- Using a **PostSync** hook to run integration and health checks after a deployment.
- Using a **SyncFail** hook to run clean-up or finalizer logic if a Sync operation fails. SyncFail hooks are only available starting in v1.2

Refer: [sample post Sync hook to queue Azure pipeline](https://dev.azure.com/csedevops/GitOps/_git/azure-vote-app-deployment?path=%2Fhelm-azure-vote-app-deployment%2Fazure-vote%2Ftemplates%2Fpost-sync-hook.yaml&version=GBmaster&_a=contents) 



![multicluster](./images/argocd-synchooks.png)