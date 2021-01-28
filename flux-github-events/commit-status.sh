# see https://docs.github.com/en/rest/reference/repos#create-a-commit-status
export TOKEN=<TOKEN>

# curl -X POST -H "Authorization: token $TOKEN>" \
#      -d '{"state":"success"}' \
#      https://api.github.com/repos/kaizentm/gitops-manifests/statuses/c0ca84a63e42797618313a5245a659c736f5ff81

curl -v -H "Authorization: token $TOKEN" -H "Content-Type: application/json" \
        -d '{"state": "pending", "description": "Reconcilation underway.", "context": "Kustomization" }' \
       "https://api.github.com/repos/kaizentm/gitops-manifests/statuses/146ac7517cb1442260191e792f55991f242ffaff"


curl -v -H "Authorization: Basic $B64_PAT" -H "Content-Type: application/json" \
        -d '{"state": "succeeded", "description": "Reconcilation succeeded.", "context": "Kustomization" }' \
       "https://api.github.com/repos/kaizentm/gitops-manifests/statuses/c0ca84a63e42797618313a5245a659c736f5ff81"


curl -H "Content-Type: application/json" \
     -d '{"involvedObject":{"kind":"Kustomization","namespace":"flux-system","name":"flux-system","uid":"ac2f66bc-bfb7-41b8-afd9-d408a7e132b1","apiVersion":"kustomize.toolkit.fluxcd.io/v1beta1","resourceVersion":"14534183"}, \
          "severity":"info", \
          "timestamp":"2021-01-20T00:13:11Z", \
          "message":"deployment.apps/azure-vote-back configured\ndeployment.apps/azure-vote-front configured\nservice/azure-vote-back configured\nservice/azure-vote-front configured\n",
          "reason":"Progressing", \
          "metadata":{"revision":"master/c0ca84a63e42797618313a5245a659c736f5ff81"}, \
          "reportingController":"kustomize-controller", \
          "reportingInstance":"kustomize-controller-5cfb78859c-nv8gb"}' \
     http://localhost:4293/