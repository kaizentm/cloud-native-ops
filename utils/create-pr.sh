# See https://github.com/microsoft/bedrock/blob/master/gitops/azure-devops/build.sh

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

pr_user_name="Git Ops"
pr_user_emaiL="agent@gitops.com"

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
echo "Create a PR to $DEST_BRANCH" 
export AZURE_DEVOPS_EXT_PAT=$PAT 
echo $PAT | az devops login --org="https://dev.azure.com/csedevops"  
az repos pr create --description="Deploy to Dev" --source-branch="deploy/20201209.16" --target-branch=dev --org="https://dev.azure.com/csedevops" --project="GitOps" --repository=azure-vote-app-deployment
az repos pr create --description="Deploy to $ENV_NAME" --source-branch=$deploy_branch_name --target-branch=$DEST_BRANCH \
--org="https://dev.azure.com/csedevops" --project="GitOps" --repository=azure-vote-app-deployment
