# Microservice Developer Inner Loop

This document covers the developer inner loop when building a microservice for Kubernetes with GitOps. It is intended to be performed from the local developer machine, and covers the following activities:

1. Build - Application code and Docker images
2. Test - Application code, deployment, end-to-end tests
3. Debug - Debugging in a cluster environment with interlinked microservices

These approaches are designed to work on devices with limited resources compared to the production environment, such as a laptop.

## Cluster environment

### Development Cluster

At a minimum, development resources should be isolated from the production cluster. Resources are commonly split by developer or feature branch. In a single cluster scenario, this can be achieved by using namespaces to split resources logically. Alternatively, multiple clusters may be created to isolate resources.

### Local Cluster

Using a local cluster on a developer's machine may be desirable if a developer cluster is not possible. For example, a local cluster might be needed if:

- Microservice deployment affects shared resources
- Developer connections are unstable or have insufficient bandwidth
- Resource changes or deployments are expensive (for example, restricted by security policy)
- Working offline is desired

On the other hand, a local cluster may not be feasible if:

- Resources are limited on the developer machine
- A local cluster cannot match the architecture of the remote environment
- Dependencies use significant bandwidth

For a local cluster, [**k3s**](https://k3s.io/) is sufficient for most use cases. Using the dockerized version [**k3d**](https://k3d.io/), it is easy to spin up a new cluster in seconds on just about any OS and major architecture.

In order to stay lightweight, k3s has design choices that may not be representative of the production cluster, for example ingress. Alternative components may be swapped in at a cost of increased resource usage. Additionally, k3s does not support some legacy features of the full Kubernetes distribution. In this case there are other local cluster options with full compatibility such as [**kind**](https://kind.sigs.k8s.io/) that are not as lightweight.

## Preferred Inner Loop - Ingress Redirection

Traditionally, code changes on a developer machine can necessitate a docker image rebuild and remote deployment. Ingress redirection allows development to take place on the local dev machine, but without the hassle of repeatedly building and redeploying.

[Bridge to Kubernetes](https://code.visualstudio.com/docs/containers/bridge-to-kubernetes) is a extension for both Visual Studio and Visual Studio Code that facilitates this local development. In this model, the inner loop steps are:

- Develop the microservice outside of a container using preferred tooling
- Build and run unit tests
- Debug by seamlessly redirecting the service on the remote cluster to your local machine. The service can either be entirely redirected, or a subdomain can be enabled without affecting the remote service.
- Repeat the process until a resource change is required on the remote cluster, or the microservice is ready to be checked in.

The benefits of using this method include:

- Devs can run their preferred tooling without having to deploy it to the cluster environment
- All dependent microservices are available as hostname redirects, allowing realistic testing scenarios
- Other team members can use the service while it is being debugged
- No additional tooling needs to be deployed to the cluster apart from the ingress redirection

Bridge to Kubernetes may not be feasible if:

- Ingress cannot be redirected due to policy or an unsupported scenario
- High bandwidth requirements between dependent microservices
- Use of Visual Studio Code dev containers (not currently supported by Bridge to Kubernetes)
- No administrator access to the local dev machine

# Alternative Method - File Sync

If Bridge to Kubernetes is not feasible, another method is to use a solution that automates the process of updating code and images during the inner loop.

There are a few options for this method, but the common mechanism is a component that runs on the local machine and watches for changes to the source files. When the source files are changed, the files are automatically sent to the target container and the container restarts if necessary. In some cases, the docker image will need to be rebuilt and redeployed - the service takes care of this flow too.

The main downside with this method is that a definition of the target environment needs to be written. For a very small service this may be trivial; for a mature service in a complex production environment, it can be quite difficult. Generally once the definition has been written it can be shared amongst team members. Environments that rely on Helm and similar technologies may require additional configuration.

The most lightweight version of this approach is [Skaffold](https://skaffold.dev/). Skaffold has limited language support compared to other solutions, but it is the easiest to get up and running.

An alternative is [Devspace](http://devspace.sh/) which has wider language support and additional features, but may need a more lengthy configuration compared to Skaffold.
