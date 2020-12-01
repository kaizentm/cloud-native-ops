# Generates K8s manifests from Helm + Kustomize templates
# Uses env variables to substitute values 
# Requires to be installed:  
#   - helm 
#   - kubectl
#   - envsubst (https://command-not-found.com/envsubst)
# 

# For the Azure-Vote sample the following env varuables are supposed to be initialized: 
export VOTE_APP_TITLE='Awesome Voting App'
export AZURE_VOTE_IMAGE_REPO=gitopsflowacr.azurecr.io/azvote
# export FRONTEND_IMAGE=v3
# export BACKEND_IMAGE=6.0.8
export TARGET_NAMESPACE=DEV

# Usage:
# generate-manifests.sh FOLDER_WITH_MANIFESTS GENERATED_MANIFESTS_FILE
# e.g.:
# generate-manifests.sh cloud-native-ops/azure-vote/manifests gen_manifests.yaml


# Substitute env variables in all yaml files in the manifest folder
for file in `find $1 -name '*.yaml'`; do envsubst <"$file" > "$file"1 && mv "$file"1 "$file"; done

# Generate manifests
for app in `find $1 -type d -maxdepth 1 -mindepth 1`; do \
  helm template "$app"/helm > "$app"/kustomize/base/manifests.yaml && \
  kubectl kustomize "$app"/kustomize/base >> $2 && \
  cat $2; \
done
pwd

