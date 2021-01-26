FROM python:3.7-slim

ENV APP_HOME /app
ENV WORKERS 1
ENV THREADS 8
ENV PREDICTIVE_UNIT_SERVICE_PORT 8080
WORKDIR $APP_HOME
COPY gitops_event_handler.py github_gitops.py requirements.txt ./
ENV PYTHONUNBUFFERED=1

ENV AZDO_ORG_URL="https://api.github.com/repos/kaizentm"
ENV AZDO_GITOPS_REPO_NAME="gitops-manifests"
ENV PAT="2594fc4cff2d8bbd2d295da6ddc6388235c5ded8" 

RUN pip install --no-cache-dir -r ./requirements.txt

CMD ["sh","-c","gunicorn --bind 0.0.0.0:$PREDICTIVE_UNIT_SERVICE_PORT --workers $WORKERS --threads $THREADS gitops_event_handler"]