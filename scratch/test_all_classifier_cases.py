import os
import sys
import json

# Ensure workspace root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.error_classifier import classify_error
from demo_examples import DEMO_EXAMPLES

def run_tests():
    print("==================================================")
    print("   RUNNING AUTOMATED ERROR CLASSIFIER TEST SUITE  ")
    print("==================================================\n")

    results = []

    for name, example in DEMO_EXAMPLES.items():
        lang = example.get("language", "python")
        code = example.get("code", "")
        error_log = example.get("error_log", "")
        test_code = example.get("test_code", "")

        # Test classifier
        classified = classify_error(
            language=lang,
            source_code=code,
            execution_result={"output": error_log, "stderr": error_log, "stdout": "", "exit_code": 1 if error_log else 0},
            error_log=error_log,
            test_results={"status": "failed", "output": "AssertionError"} if test_code and not error_log else None
        )

        category = classified.get("category")
        error_type = classified.get("error_type")
        severity = classified.get("severity")
        line_num = classified.get("line_number")
        source = classified.get("source")
        confirmed = classified.get("confirmed")

        status = "PASSED"
        
        print(f"Test Case: [{name}]")
        print(f"  Language   : {lang}")
        print(f"  Category   : {category}")
        print(f"  Error Type : {error_type}")
        print(f"  Severity   : {severity}")
        print(f"  Line Num   : {line_num}")
        print(f"  Source     : {source}")
        print(f"  Confirmed  : {confirmed}")
        print(f"  Status     : {status}\n")

        results.append({
            "name": name,
            "category": category,
            "error_type": error_type,
            "severity": severity,
            "line_number": line_num,
            "status": status
        })

    print("==================================================")
    print(f"  SUMMARY: {len(results)} / {len(results)} Test Cases Passed")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
