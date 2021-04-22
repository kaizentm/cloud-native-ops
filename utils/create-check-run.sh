export TOKEN=bd16b68dbc0ade6c37b98429980cc352b594234b
export owner_repo='kaizentm/gitops-manifests'



curl -v -X POST -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github.antiope-preview+json" \
             -d '{"name":"name","head_sha":"b98aaee67bc964b453c6b4e3df1fc7ff4eb97a7e", "status":"in_progress", "output":{"title":"Deployment to Dev", "summary":"Waiting for PR #... to be merged and for Flux to deploy", "text":"Awesome"}}' \
            "https://api.github.com/repos/$owner_repo/check-runs"


curl -v  -H "Accept: application/vnd.github.v3+json" --fail \
            -d '{"name":"Deploy dev","head_sha":"276c7f33ccbed8745e3ec4867b854766c59f14f6"}' \
            "https://api.github.com/repos/$owner_repo/check-runs"


curl -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github.v3+json"  \
            "https://api.github.com/repos/$owner_repo/commits/b258e3df18bf5efd91a75687d08f996ce9942c14"

    

/repos/{owner}/{repo}/commits/{ref}/check-suites