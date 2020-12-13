from flask import Flask, request
from azdo_gitops import AzureDevOpsGitOps


application = Flask(__name__)


@application.route("/gitopsphase/", methods=['POST'])
def gitopsphase():
    payload = request.get_json()

    print(f'GitOps phase: {payload}')
    
    azdo_gitops = AzureDevOpsGitOps()
    azdo_gitops.process_gitops_phase(payload)

    return f'GitOps phase: {payload}', 200    


if __name__ == "__main__":
    application.run(host='0.0.0.0')