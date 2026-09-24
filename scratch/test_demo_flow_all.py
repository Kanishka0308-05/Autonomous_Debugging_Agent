import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from demo_examples import DEMO_EXAMPLES
from language_adapters.python.adapter import PythonAdapter
from language_adapters.java.adapter import JavaAdapter
from utils.error_classifier import classify_error
from orchestration.graph import debugging_app

def test_python_demo_flow():
    print("--------------------------------------------------")
    print("TEST 1: Python Demo Flow (ZeroDivisionError)")
    print("--------------------------------------------------")

    ex = DEMO_EXAMPLES["Python: ZeroDivisionError"]
    demo_dir = tempfile.mkdtemp(prefix="demo_workspace_")
    demo_file_path = os.path.join(demo_dir, ex["filename"])
    with open(demo_file_path, "w", encoding="utf-8") as f:
        f.write(ex["code"])

    adapter = PythonAdapter(demo_dir)
    init_exec = adapter.run_project()

    classified = classify_error(
        language="python",
        source_code=ex["code"],
        execution_result=init_exec,
        error_log=ex["error_log"]
    )

    print("Classified Error Category:", classified["category"])
    print("Classified Error Type:", classified["error_type"])

    state = {
        "input_mode": "single_file",
        "project_path": demo_dir,
        "project_name": ex["filename"],
        "language": "python",
        "build_system": "pytest",
        "source_code": ex["code"],
        "error_log": ex["error_log"],
        "execution_result": init_exec,
        "classified_error": classified,
        "test_code": ex.get("test_code", ""),
        "code_analysis": None,
        "bug_investigation": None,
        "root_cause": None,
        "candidate_fix": None,
        "test_results": None,
        "verification_result": None,
        "iteration_count": 0,
        "max_iterations": 3,
        "history": [],
        "final_report": None,
        "is_mock_mode": True
    }

    final_state = debugging_app.invoke(state)
    print("Pipeline Execution Completed!")
    print("Verification Status:", final_state.get("verification_result", {}).get("status"))
    assert classified["category"] == "RUNTIME_ERROR"
    assert classified["error_type"] == "ZeroDivisionError"
    print("[OK] Test 1 PASSED cleanly!\n")

def test_java_demo_flow():
    print("--------------------------------------------------")
    print("TEST 2: Java Demo Flow (ArithmeticException)")
    print("--------------------------------------------------")

    ex = DEMO_EXAMPLES["Java: ArithmeticException"]
    demo_dir = tempfile.mkdtemp(prefix="demo_workspace_")
    demo_file_path = os.path.join(demo_dir, ex["filename"])
    with open(demo_file_path, "w", encoding="utf-8") as f:
        f.write(ex["code"])

    adapter = JavaAdapter(demo_dir)
    init_exec = adapter.run_project()

    classified = classify_error(
        language="java",
        source_code=ex["code"],
        execution_result=init_exec,
        error_log=ex["error_log"]
    )

    print("Classified Error Category:", classified["category"])
    print("Classified Error Type:", classified["error_type"])

    state = {
        "input_mode": "single_file",
        "project_path": demo_dir,
        "project_name": ex["filename"],
        "language": "java",
        "build_system": "java-direct",
        "source_code": ex["code"],
        "error_log": ex["error_log"],
        "execution_result": init_exec,
        "classified_error": classified,
        "test_code": "",
        "code_analysis": None,
        "bug_investigation": None,
        "root_cause": None,
        "candidate_fix": None,
        "test_results": None,
        "verification_result": None,
        "iteration_count": 0,
        "max_iterations": 3,
        "history": [],
        "final_report": None,
        "is_mock_mode": True
    }

    final_state = debugging_app.invoke(state)
    print("Pipeline Execution Completed!")
    print("Verification Status:", final_state.get("verification_result", {}).get("status"))
    assert classified["category"] == "RUNTIME_ERROR"
    assert classified["error_type"] == "ArithmeticException"
    print("[OK] Test 2 PASSED cleanly!\n")

def test_no_error_clean_code():
    print("--------------------------------------------------")
    print("TEST 3: Clean Code Demo (No Error Detected)")
    print("--------------------------------------------------")

    ex = DEMO_EXAMPLES["Python: Clean Working Code"]
    demo_dir = tempfile.mkdtemp(prefix="demo_workspace_")
    demo_file_path = os.path.join(demo_dir, ex["filename"])
    with open(demo_file_path, "w", encoding="utf-8") as f:
        f.write(ex["code"])

    adapter = PythonAdapter(demo_dir)
    init_exec = adapter.run_project()

    classified = classify_error(
        language="python",
        source_code=ex["code"],
        execution_result=init_exec,
        error_log=""
    )

    print("Classified Error Category:", classified["category"])
    assert classified["category"] == "NO_ERROR"
    print("[OK] Test 3 PASSED cleanly!\n")

if __name__ == "__main__":
    test_python_demo_flow()
    test_java_demo_flow()
    test_no_error_clean_code()
