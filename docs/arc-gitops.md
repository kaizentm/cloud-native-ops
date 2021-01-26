# Arc GitOps configurations

These are specific steps for the repo based on this [Azure docs article](https://docs.microsoft.com/azure/azure-arc/kubernetes/use-gitops-connected-cluster).  This only works for non-AKS clusters.

`az k8sconfiguration create --name cluster-config --cluster-name gitopsaks --resource-group gitopsrg --operator-instance-name cluster-config --operator-namespace cluster-config --repository-url git@ssh.dev.azure.com:v3/csedevops/GitOps/cloud-native-ops --ssh-private-key-file /mnt/c/src/azdo/cloud-native-ops/fluxkey --scope cluster --cluster-type connectedClusters`

## Arc GitOps configuration for AKS

These are specific steps for the repo based on this [private preview doc](https://github.com/Azure/azure-arc-kubernetes-preview/blob/master/docs/use-gitops-in-aks-cluster.md)

Create the cluster:

```bash
export AKS_NAME=arcfluxpreview
export RESOURCE_GROUP=arcfluxpreviewrg
export LOCATION=eastus
export NODE_COUNT=1
export K8S_VERSION=1.19.6
export VM_SIZE=Standard_DS2_v2
az group create -n $RESOURCE_GROUP -l $LOCATION
az aks create -n $AKS_NAME -g $RESOURCE_GROUP -l $LOCATION \
  --kubernetes-version $K8S_VERSION \
  --node-count $NODE_COUNT \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 3 \
  --node-vm-size $VM_SIZE \
  --enable-managed-identity \
  --network-plugin azure \
  --generate-ssh-keys
<!--
  --dns-name-prefix $AKS_NAME \
  --service-principal $AKS_SERVICE_PRICIPAL \
  --client-secret $AKS_SERVICE_PRINCIPAL_SECRET
-->

# Get kube config file
az aks get-credentials -n $AKS_NAME -g $RESOURCE_GROUP

# Enable the AKS GitOps addon
az aks enable-addons -a gitops -n $AKS_NAME -g $RESOURCE_GROUP
```

### Enable AKS to access private ACR

`az aks update -n $AKS_NAME -g $RESOURCE_GROUP --attach-acr gitopsflowacr`

### Create the GitOps configuration for the cluster

Additional options can be found in [this public article](https://docs.microsoft.com/azure/azure-arc/kubernetes/use-gitops-connected-cluster).

```bash
az k8sconfiguration create \
    --name voteapp-config \
    --cluster-name $AKS_NAME \
    --resource-group $RESOURCE_GROUP \
    --operator-instance-name votens-operator \
    --repository-url git@ssh.dev.azure.com:v3/csedevops/GitOps/azure-vote-app-deployment \
    --ssh-private-key-file /mnt/c/src/azdo/cloud-native-ops/fluxkey \
    --scope namespace \
    --operator-namespace vote \
    --operator-params='--git-path=azure-vote-app-deployment' \
    --cluster-type managedclusters
```

### Show GitOps configurations for the cluster

`az k8sconfiguration list --resource-group $RESOURCE_GROUP --cluster-name $AKS_NAME  --cluster-type managedClusters`

Alternatively visit the GitOps sub-item for the AKS cluster in the Azure preview portal [https://aka.ms/AKSGitOpsPreview](https://aka.ms/AKSGitOpsPreview).
