#!/bin/bash

## TODO: what about slash categorization, e.g. feature/tcare/test
## TODO: more sanitization of args
## TODO: what if the environment is partially created?

# Checks if a feature environment already exists.

usage() {
    echo "Usage: $0 -p <feature branch prefix> -b <feature branch name>" 1>&2
    exit 1
}

while getopts "p:b:" option;
    do
    case "$option" in
        p ) PREFIX=${OPTARG};;
        b ) BRANCH=${OPTARG};;
        * ) usage;;
    esac
done

# All args required
if [[ -z "${PREFIX}" ]] || [[ -z "${BRANCH}" ]]; then
    usage
fi

echo "Prefix: $PREFIX"
echo "Branch: $BRANCH"

# Prefix should have a trailing slash
REGEXP="\w+/"
if ! [[ ${PREFIX} =~ $REGEXP ]]; then
    echo "Prefix must end with a /" 1>&2
    usage
fi

# Branch must be prefixed by the prefix
if [[ ${BRANCH#${PREFIX}} == $BRANCH ]]; then
    echo "Branch must be prefixed by $PREFIX" 1>&2
    usage
fi

# Remove prefix
FEATURE=${BRANCH#${PREFIX}}

echo "Environment name: $FEATURE"

echo ""
echo "Checking for envrionment..."

# Check the environment branch exists
git rev-parse --verify --quiet $BRANCH > /dev/null
if [[ $? -ne 0 ]]; then
    echo "No $BRANCH branch for environment $FEATURE found"
    exit 1
fi

# Check the branch name doesn't conflict with a non-prefixed environment
# E.g. feature/dev shouldn't conflict with dev
git rev-parse --verify --quiet $FEATURE > /dev/null
if [[ $? -ne 1 ]]; then
    echo "Invalid feature environment name - conflict with $FEATURE"
    exit 1
fi

echo "- Branch exists and is valid"

kubectl get namespace $NAMESPACE > /dev/null
if [[ $? -ne 0 ]]; then
    echo "Feature environment namespace not found"
    exit 1
fi

echo "- Namespace exists"

kubectl get -n flux-system GitRepository $FEATURE > /dev/null
if [[ $? -ne 0 ]]; then
    echo "Flux git repository entry does not exist"
    exit 1
fi

echo "- Flux GitRepository entry exists"

echo "Everything OK, environment exists!"

exit 0