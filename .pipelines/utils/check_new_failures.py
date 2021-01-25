import base64
import os
import requests
import sys

BASE_URL = "https://vstmr.dev.azure.com"
ORG_ID = 'csedevops'
PROJECT_ID = os.getenv('SYSTEM_TEAMPROJECTID')
BUILD_ID = os.getenv('BUILD_BUILDID')
PAT = os.getenv('SYSTEM_ACCESSTOKEN')

# https://vstmr.dev.azure.com/csedevops/703aeefb-31bf-46e0-a934-125e19f15931/_apis/testresults/metrics?pipelineId=11622&metricNames=3
def get_test_result_metrics():
    url = f'{BASE_URL}/{ORG_ID}/{PROJECT_ID}/_apis/testresults/metrics?pipelineId={BUILD_ID}&metricNames=3&api-version=6.1-preview.1'

    print(url)

    token = base64.b64encode(f':{PAT}'.encode("ascii")).decode("ascii")
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type' : 'application/json'
    }

    response = requests.get(url=url, headers=headers)
    # Throw appropriate exception if request failed
    response.raise_for_status()

    print(response.content)

    metrics_dict = response.json()
    print(metrics_dict)

    return metrics_dict

# Given a dictionary of test result metrics, return the new failure count.
def get_new_failures(metrics_dict):
    # We should always get results, so don't null check.
    results = metrics_dict['resultsAnalysis']

    failure_info = results.get('testFailuresAnalysis')
    if not failure_info:
        return 0

    new_failures = failure_info.get('newFailures')
    if not new_failures:
        return 0

    return new_failures['count']


if __name__ == "__main__":
    metrics_dict = get_test_result_metrics()
    error_count = get_new_failures(metrics_dict)
    print(error_count, file=sys.stderr)
    print('##[warning]Warning message ' + error_count)
