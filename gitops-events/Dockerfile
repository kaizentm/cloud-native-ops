FROM python:3.7-slim

ENV APP_HOME /app
ENV WORKERS 1
ENV THREADS 8
ENV PREDICTIVE_UNIT_SERVICE_PORT 8080
WORKDIR $APP_HOME
COPY gitops_event_handler.py azdo_gitops.py requirements.txt ./
ENV PYTHONUNBUFFERED=1

ENV AZDO_ORG_URL="https://dev.azure.com/csedevops/GitOps"
ENV PAT=PAT
ENV GITOPS_APP_URL="https://argodashboard.westus.cloudapp.azure.com/applications/az-vote-dev"

RUN pip install --no-cache-dir -r ./requirements.txt

CMD ["sh","-c","gunicorn --bind 0.0.0.0:$PREDICTIVE_UNIT_SERVICE_PORT --workers $WORKERS --threads $THREADS gitops_event_handler"]