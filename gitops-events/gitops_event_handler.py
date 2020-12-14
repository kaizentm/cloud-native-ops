from flask import Flask, request
from azdo_gitops import AzureDevOpsGitOps


application = Flask(__name__)

temp_data = {}

@application.route("/gitopsphase/", methods=['POST'])
def gitopsphase():
    payload = request.get_json()

    print(f'GitOps phase: {payload}')
    
    azdo_gitops = AzureDevOpsGitOps()
    azdo_gitops.process_gitops_phase(payload, temp_data)

    return f'GitOps phase: {payload}', 200    

@application.route("/deploy", methods=['POST'])
def deploy():
    payload = request.get_json()

    print(f'deploy: {payload}')
    
    global temp_data
    temp_data = payload

    return f'deploy: {payload}', 200    

if __name__ == "__main__":
    application.run(host='0.0.0.0')