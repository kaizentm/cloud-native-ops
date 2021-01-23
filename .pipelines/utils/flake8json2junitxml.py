import argparse
import json
from junit_xml import TestSuite, TestCase
from xml.sax.saxutils import quoteattr
import sys

input = json.load(sys.stdin)

test_cases = []

for entries in input.values():
    for entry in entries:
        location = f"{entry['filename']}:{entry['line_number']}:{entry['column_number']}"

        # Azure DevOps JUnit field mapping: https://docs.microsoft.com/en-us/azure/devops/pipelines/tasks/test/publish-test-results?view=azure-devops&tabs=junit%2Cyaml
        test_case = TestCase(
            name=f"{entry['code']}: {entry['text']}",
            classname=entry['filename'],
            line=entry['line_number']
        )

        # Show the source line that caused the error.
        err_text = f"{entry['code']}:\n\t{entry['physical_line']}"
        # Escape for use as an XML attribute value, and remove
        # the extra single or double quotes at the ends.
        escaped_err = quoteattr(err_text)[1:-1]

        test_case.add_failure_info(
            message=escaped_err,
            output=location,
            failure_type="Flake8"
        )

        test_cases.append(test_case)

ts = TestSuite("Flake8 Python Linter", test_cases)
print(TestSuite.to_xml_string([ts]))
with open('flake8-testresults.xml', 'w') as f:
    TestSuite.to_file(f, [ts], prettyprint=False)

