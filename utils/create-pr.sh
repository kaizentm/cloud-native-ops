#!/usr/bin/env bash

while getopts "s:d:r:b:i:t:e:" option;
    do
    case "$option" in
        s ) SOURCE_FOLDER=${OPTARG};;
        d ) DEST_FOLDER=${OPTARG};;
        r ) DEST_REPO=${OPTARG};;
        b ) DEST_BRANCH=${OPTARG};;
        i ) DEPLOY_ID=${OPTARG};;
        t ) TOKEN=${OPTARG};;
        e ) ENV_NAME=${OPTARG};;
    esac
done

set -euo pipefail  # fail on error

pr_user_name="Git Ops"
pr_user_email="agent@gitops.com"

git config --global user.email $pr_user_email
git config --global user.name $pr_user_name

# Clone manifests repo
echo "Clone manifests repo"
repo_url="${DEST_REPO#http://}"
repo_url="${DEST_REPO#https://}"
repo_url="https://automated:$TOKEN@$repo_url"

echo "git clone $repo_url -b $DEST_BRANCH --depth 1 --single-branch"
git clone $repo_url -b $DEST_BRANCH --depth 1 --single-branch
repo=${DEST_REPO##*/}
repo_name=${repo%.*}
cd "$repo_name"
echo "git status"
git status

# Create a new branch 
deploy_branch_name=deploy/$DEPLOY_ID

echo "Create a new branch $deploy_branch_name"
git checkout -b $deploy_branch_name

# Add generated manifests to the new deploy branch
mkdir -p $DEST_FOLDER
cp $SOURCE_FOLDER/* $DEST_FOLDER/
git add -A
git status
git commit -m "deployment $DEPLOY_ID"

# Push to the deploy branch 
echo "Push to the deploy branch $deploy_branch_name"
echo "git push --set-upstream $repo_url $deploy_branch_name"
git push --set-upstream $repo_url $deploy_branch_name

# Create a PR 
# Old version of Azure CLI
# Just Rest API?
echo "Create a PR to $DEST_BRANCH" 
# az upgrade --all -y
# export AZURE_DEVOPS_EXT_PAT=$PAT 
# echo tki74xnggmqnmbgaxjizsdfj7jyxqj6e6i4rl5e4lvqud6vaatyq | az devops login --organization https://dev.azure.com/csedevops
# az repos pr create --description="Deploy to Dev" --source-branch="deploy/20201209.16" --target-branch=dev --org="https://dev.azure.com/csedevops" --project="GitOps" --repository=azure-vote-app-deployment
# az repos pr create --description="Deploy to $ENV_NAME" --source-branch=$deploy_branch_name --target-branch=$DEST_BRANCH \
# --org="https://dev.azure.com/csedevops" --project="GitOps" --repository=azure-vote-app-deployment

# curl -v -H "Authorization: Basic $B64_PAT" -H "Content-Type: application/json"\
#         -d '{"sourceRefName":"refs/heads/deploy/20201209.16", "targetRefName":"refs/heads/dev", "description":"Deploy to Dev", "title":"Deploy to Dev"}' \
#        'https://dev.azure.com/csedevops/GitOps/_apis/git/repositories/6b37c26c-06e2-45ae-8076-7c37aa34510d/pullrequests?api-version=6.1-preview.1'       

# curl -v -H "Authorization: Basic $B64_PAT" -H "Content-Type: application/json"\
#         -d '{"sourceRefName":"refs/heads/deploy/20201209.22", "targetRefName":"refs/heads/dev", "description":"Deploy to Dev", "title":"Deploy to Dev"}' \
#        'https://dev.azure.com/csedevops/GitOps/_apis/git/repositories/azure-vote-app-deployment/pullrequests?api-version=6.1-preview.1'              

B64_PAT=$(printf ":$TOKEN" | base64)
curl -v -H "Authorization: Basic $B64_PAT" -H "Content-Type: application/json" --fail \
        -d '{"sourceRefName":"refs/heads/$deploy_branch_name", "targetRefName":"refs/heads/$DEST_BRANCH", "description":"Deploy to $ENV_NAME", "title":"deployment $DEPLOY_ID"}' \
       $SYSTEM_COLLECTIONURI$SYSTEM_TEAMPROJECT/_apis/git/repositories/$repo_name/pullrequests?api-version=6.1-preview.1      
