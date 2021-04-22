# see https://docs.microsoft.com/en-us/rest/api/azure/devops/git/statuses/create?view=azure-devops-rest-6.0
export TOKEN=<TOKEN>
B64_PAT=$(printf ":$TOKEN" | base64)
# curl -v -H "Authorization: Basic $B64_PAT" -H "Content-Type: application/json" --fail \
#         -d '{"sourceRefName":"refs/heads/'$deploy_branch_name'", "targetRefName":"refs/heads/'$DEST_BRANCH'", "description":"Deploy to '$ENV_NAME'", "title":"deployment '$DEPLOY_ID'"}' \
#        "$SYSTEM_COLLECTIONURI$SYSTEM_TEAMPROJECT/_apis/git/repositories/$repo_name/pullrequests?api-version=6.1-preview.1"      


curl -v -H "Authorization: Basic $B64_PAT" -H "Content-Type: application/json" \
        -d '{"state": "pending", "description": "The changes are being applied", "targetUrl": "https://argodashboard.westus.cloudapp.azure.com/applications/az-vote-dev", "context": {"name": "Degraded", "genre": "Health"} }' \
       "https://dev.azure.com/csedevops/GitOps/_apis/git/repositories/azure-vote-app-deployment/commits/0d46b0e0f75c17259063e28da83a3b1be738bb1d/statuses?api-version=6.0"


curl -v -H "Authorization: Basic $B64_PAT" -H "Content-Type: application/json" \
        -d '{"state": "succeeded", "description": "The changes have been succesfully applied", "targetUrl": "https://argodashboard.westus.cloudapp.azure.com/applications/az-vote-dev", "context": {"name": "Healthy", "genre": "Health"} }' \
       "https://dev.azure.com/csedevops/GitOps/_apis/git/repositories/azure-vote-app-deployment/commits/0d46b0e0f75c17259063e28da83a3b1be738bb1d/statuses?api-version=6.0"


curl -H "Content-Type: application/json" -d '{"commitid": "505be9ff4eda9d1146326998ebe5067af00a2d8b", "state": "Succeeded", "health": "Healthy", "message": "successfully synced (all tasks run)"}' http://localhost:4293/gitopsphase