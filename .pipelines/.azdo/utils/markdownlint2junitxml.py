import json
from junit_xml import TestSuite, TestCase
import sys

input = json.load(sys.stdin)

test_cases = []

for entry in input:
    location = f"{entry['filename']}:{entry['line']}"

    # Azure DevOps JUnit field mapping: https://docs.microsoft.com/en-us/azure/devops/pipelines/tasks/test/publish-test-results?view=azure-devops&tabs=junit%2Cyaml
    test_case = TestCase(
        name=f"{entry['rule']}: {entry['description']}",
        classname=entry['filename'],
        line=entry['line']
    )

    test_case.add_failure_info(
        message=entry['description'],
        output=location,
        failure_type="markdownlint"
    )

    test_cases.append(test_case)

ts = TestSuite("Markdownlint Markdown Linter", test_cases)
print(TestSuite.to_xml_string([ts]))
with open('markdownlint-testresults.xml', 'w') as f:
    TestSuite.to_file(f, [ts], prettyprint=False)
