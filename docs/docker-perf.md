# Optimizing Docker Build Performance

To get the best performance out of Docker when building images, there are multiple levels of best practices to follow.

## Dockerfile level

Follow [best practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/) as outlined in the Docker documentation. For example, optimize ordering of layers so that frequently changed assets are copied last.

## Driver level

The legacy Docker driver is being deprecated in favor of BuildKit. It is currently opt-in, but shipping with Docker.

Use [BuildKit](https://docs.docker.com/develop/develop-images/build_enhancements/) to leverage improved build speed, especially in multi-stage images. Parts of these images can be done in parallel, e.g. multiple FROM statements can have the base images downloaded in parallel. .NET Core makes use of this pattern, by having an intermediate SDK image for building and a reduced runtime image for the running the app.

## Pipeline level

Utilize [lazy image building](/.pipelines/build-container-template.yaml) so that images are built only when the source code changes, rather than building the image for any commit to the repo.

- Important: If this approach is used, a non-cached build should be performed at a regular cadence (e.g. daily) so that security and bug fixes are picked up in dependencies. This also allows for earlier detection of breaking changes in dependencies.

## Builder level

### Intra-build layer caching

Depending on image complexity, image size, builder bandwidth, and builder disk performance, intra-build caching may improve performance. Take into consideration the factors below to see if they might give a performance boost in your scenario.

#### Built in Docker cache

Docker caches layers locally. For hosted agents, this cache will not persist as the VMs are destroyed after each use. However if the customer is using custom agents that have persistent storage between builds, any reused layers will already be available on disk. This will not help the case of multiple agents where the same builder does not get reused each time.

#### Import/export based cache

Docker supports serialization of images using the import and export commands.  The primary benefit of caching is to save computation time. For example, if intermediate steps of an image do compilation that takes 10mins, then it's plausible that the cache download, import, export, and upload time could be less than the compilation. On the other hand, a cache miss may become very expensive if the key is harder to determine beforehand.

The intermediate format is a .tar file. The disadvantage of this method is that the import and export require a disk copy, and are therefore bound by disk I/O. On hosted agents, disk performance is limited. BYO agents on VMs can be specified with SSDs that will help overcome this bottleneck.

Between builds, the intermediate format is stored remotely via upload/download. Take the network bandwidth into account when considering this option. This can be implemented in a few ways.

Using Azure Pipelines only, there is a [caching task](https://docs.microsoft.com/en-us/azure/devops/pipelines/release/caching?view=azure-devops#docker-images) that can store read-only blobs with a key. Consider the factors that will be needed for the key e.g. OS platform, version, etc. Underneath, Azure uses a dedeuplicated and compressed back store that is reconstructed and streamed on demand. Because of this, the remote can be a bottleneck.

Another manual approach is to use ACR to store a cache image. It may be as simple as just prefetching the 'latest' tag, or perhaps a dedicated 'cache' tag. That can then be pushed/pulled as needed.

### ACR Tasks

Rather than building on the Azure Pipelines agent, build tasks can be offloaded to ACR Tasks. One performance implication of this is that the build context needs to be transferred, which may not scale for larger repositories with bandwidth limitations.

ACR Tasks offers both hosted and dedicated agents using VMSS. The hosted agents have roughly the same performance as the Azure Pipelines agents. Offloading image tasks to ACR allows for customization of agent resources independent of the Azure Pipelines agents.

ACR Tasks also allows some operations to be performed without involving Azure Pipelines, for example, updating an image and running test [when the base image changes](https://docs.microsoft.com/en-us/azure/container-registry/container-registry-tutorial-base-image-update). This can potentially free up Azure Pipelines resources to be used for other tasks.
