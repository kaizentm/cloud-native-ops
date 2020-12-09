# See https://github.com/microsoft/bedrock/blob/master/gitops/azure-devops/build.sh

#!/usr/bin/env bash

while getopts "s:d:r:b:i:t:" option;
    do
    case "$option" in
        s ) SOURCE_FOLDER=${OPTARG};;
        d ) DEST_FOLDER=${OPTARG};;
        r ) DEST_REPO=${OPTARG};;
        b ) DEST_BRANCH=${OPTARG};;
        i ) DEPLOY_ID=${OPTARG};;
        t ) PAT=${OPTARG};;
    esac
done

export PR_USER_NAME="Git Ops"
export PR_USER_EMAIL="agent@gitops.com"

git config --global user.email $PR_USER_EMAIL
git config --global user.name $PR_USER_NAME

# Clone manifests repo
echo "Clone manifests repo"
repo_url="${DEST_REPO#http://}"
repo_url="${DEST_REPO#https://}"
repo_url="https://automated:$PAT@$repo_url"

echo "git clone $repo_url -b $dest_branch --depth 1 --single-branch"
git clone $repo_url -b $dest_branch --depth 1 --single-branch
repo=${DEST_REPO##*/}
repo_name=${repo%.*}
cd "$repo_name"
echo "git status"
git status


# git checkout -b deploy/test
# cd azure-vote-app-deployment
# echo "Hi there" > test.md
# git add -A
# git commit -m 'deployment'
# git push --set-upstream origin deploy/test

# az repos pr create --description="Deploy to Dev" --source-branch="deploy/test" --target-branch=dev --org="https://dev.azure.com/csedevops" --project="GitOps" --repository=azure-vote-app-deployment
