# Generates K8s manifests from Helm + Kustomize templates
# Uses env variables to substitute values 
# Requires to be installed:  
#   - helm 
#   - kubectl
#   - envsubst (https://command-not-found.com/envsubst)
# 

# For the Azure-Vote sample the following env varuables are supposed to be initialized: 
# export VOTE_APP_TITLE='Awesome Voting App'
# export AZURE_VOTE_IMAGE_REPO=gitopsflowacr.azurecr.io/azvote
# export FRONTEND_IMAGE=v3
# export BACKEND_IMAGE=6.0.8
# export TARGET_NAMESPACE=dev
export gen_manifests_file_name='gen_manifests.yaml'

# Usage:
# generate-manifests.sh FOLDER_WITH_MANIFESTS GENERATED_MANIFESTS_FOLDER
# e.g.:
# generate-manifests.sh cloud-native-ops/azure-vote/manifests gen_manifests
# 
# the script will put Helm + Kustomize manifests with substituted variable values
# to gen_manifests/hld folder and plain yaml manifests to gen_manifests/gen_manifests.yaml file


mkdir -p $2
mkdir -p $2/hld

# Substitute env variables in all yaml files in the manifest folder
for file in `find $1 -name '*.yaml'`; do envsubst <"$file" > "$file"1 && mv "$file"1 "$file"; done



# Generate manifests
for app in `find $1 -type d -maxdepth 1 -mindepth 1`; do \
  cp -r "$app"/helm $2/hld/
  cp -r "$app"/kustomize $2/hld/

  helm template "$app"/helm > "$app"/kustomize/base/manifests.yaml && \
  kubectl kustomize "$app"/kustomize/base >> $2/$gen_manifests_file_name && \
  cat $2/$gen_manifests_file_name; \
done
pwd

