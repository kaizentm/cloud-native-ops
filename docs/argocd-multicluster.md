# Argo CD Setup for Multi-Cluster Deployment

This document highlights different ways to set up Argo CD  for multiple cluster deployment. Out-of-box Argo CD supports multiple cluster deployment from a single cluster that runs Argo CD.
<br>

To add new cluster to Argo CD using CLI: <br>

```
argocd cluster add [CONTEXTNAME]
```

**Note:** The above command installs a ServiceAccount (argocd-manager), into the kube-system namespace of that kubectl context, and binds the service account to an admin-level ClusterRole. Argo CD uses this service account token to perform its management tasks (i.e. deploy/monitoring).  

## Single Argo CD Setup for Multi-Cluster
![singlecluster](./images/single-argocd.png)

However, some teams might also choose to set up Argo CD per cluster:  

## Argo CD Setup per Cluster 
![multicluster](./images/multi-argocd.png)

<br>

| **Single Argo CD Setup**  	| **Multiple Argo CD Setup**  	|
|---	|---	|
|   Single dashboard with a unified view across multiple cluster    	|   Separate dashboard per cluster difficult to navigate. Can be mitigated when all cluster feeds to a single monitoring source.	|
| One place to configure different Argo CD configurations like  SSO, RBAC  	|  Multiple configurations to manage per cluster 	|
| Argo CD apps needs to have unique names across all clusters. This can be handled with cluster specific prefixes/cluster   	| Only Argo CD apps within the same clusters need a unique name  	|
| Huge blast radius. If this single Argo CD setup fails all deployments are halted.  	| Limited blast radius. Any failure will only halt the deployments running on the same cluster  	|
| Access to other the cluster needs to be explicitly enabled to add clusters to the this single Argo CD setup which might be security concerns for some teams.   	| Access to cluster from outside is not required for Argo CD operations  	|
|  Complex bootstrapping; requires a new cluster to be created with all configurations and ensure the master cluster has access to the newly created cluster, Only after which create Argo CD apps that can create namespaces and deploy apps. Depends on how often new clusters are created or replace the cluster. 	| Easy bootstrapping : Creating a new cluster followed by Argo CD setup, applying  Argo CD apps CRD to creates an app and deploy apps.  	|

<br>

## Cluster BootStrapping

Using **app of apps pattern** to quickly deploy apps to the newly added cluster. To implement this pattern create a single app Argo CD app that on syncing creates multiple child apps which deploys your application to single or multiple kubernetes cluster.

[Example Code](https://dev.azure.com/csedevops/GitOps/_git/azure-vote-app-deployment?version=GBmaster&path=%2Fcluster-bootstrapping)

This sample code uses helm chart to create multiple child apps with below structure: 

```bash
├── Chart.yaml
├── templates
│   ├── az-vote-app-stage.yaml    <- Argo CD app that to deploy az-vote-app to staging cluster.
│   ├── az-vote-app-prod.yaml     <- Argo CD app that to deploy az-vote-app to production cluster.
└── values.yaml
```

1. Create Argo CD parent app that above helm chart consisting of staging and prod az-vote-app:   
```
argocd app create apps \
    --dest-namespace argocd \
    --dest-server https://kubernetes.default.svc \
    --repo https://csedevops@dev.azure.com/csedevops/GitOps/_git/azure-vote-app-deployment \
    --path cluster-bootstrapping \
    --revision master	  
```
2. Sync parent App to create child app 
```
argocd app sync apps  
```
