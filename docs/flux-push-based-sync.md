# Flux v2 Push-Based Synchronization

Flux v2 is pull-based by design. Using webhook receivers, a push-based GitOps pipeline is built to react to GitHub events. Follow the [Setup Webhook Receivers](https://toolkit.fluxcd.io/guides/webhook-receivers/) guide to create a Flux v2 push-based GitOps pipeline.

We did this with our [gitops-manifest](https://github.com/kaizentm/gitops-manifests) repository and the fluxaks AKS on the davete-team Azure subscription. If you would like to see it in action, simply make a change  to any of the files in the gitops-manifest repository (e.g. change the v2 to v3 in line 24 on azure-vote-app-deployment/az-vote-front-deployment.yaml) and merge the change into master. Once the change is merged, the following happens:

- GitHub sends a Git push event to the webhook receiver
- Flux notification controller validates the event
- Flux source controller is notified about the change, pulls the change into the cluster, and updates the `GitRepository` revision
- Flux kustomize controller receives the change notification and reconciles all the `Kustomizations` that reference the `GitRepository` object