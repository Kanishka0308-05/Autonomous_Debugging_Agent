import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from language_adapters.java.adapter import JavaAdapter
from language_adapters.python.adapter import PythonAdapter
from utils.error_classifier import classify_error

def test_java_single_file():
    print("--------------------------------------------------")
    print("Testing Java Single File Execution & Classification...")
    print("--------------------------------------------------")

    temp_dir = tempfile.mkdtemp(prefix="test_java_workspace_")
    java_code = """public class Main {
    public static void main(String[] args) {
        int a = 10;
        int b = 0;
        System.out.println(a / b);
    }
}"""
    file_path = os.path.join(temp_dir, "Main.java")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(java_code)

    adapter = JavaAdapter(temp_dir)
    exec_res = adapter.run_project()

    print("Execution Result Status:", exec_res.get("status"))
    print("Exit Code:", exec_res.get("exit_code"))
    print("Output:\n", exec_res.get("output"))

    classified = classify_error(
        language="java",
        source_code=java_code,
        execution_result=exec_res,
        error_log=exec_res.get("output", "")
    )

    print("\nClassified Error Object:")
    print(json.dumps(classified, indent=2))

    assert classified["category"] == "RUNTIME_ERROR", f"Expected RUNTIME_ERROR, got {classified['category']}"
    assert classified["error_type"] == "ArithmeticException", f"Expected ArithmeticException, got {classified['error_type']}"
    assert classified["line_number"] in (5, "5", "Main.java:5"), f"Unexpected line number {classified['line_number']}"
    print("\n[OK] Java Test PASSED cleanly!")

def test_python_single_file():
    print("\n--------------------------------------------------")
    print("Testing Python Single File Execution & Classification...")
    print("--------------------------------------------------")

    temp_dir = tempfile.mkdtemp(prefix="test_py_workspace_")
    py_code = """def divide(a, b):
    return a / b

print(divide(10, 0))
"""
    file_path = os.path.join(temp_dir, "demo.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(py_code)

    adapter = PythonAdapter(temp_dir)
    exec_res = adapter.run_project()

    classified = classify_error(
        language="python",
        source_code=py_code,
        execution_result=exec_res,
        error_log=exec_res.get("output", "")
    )

    print("\nClassified Error Object:")
    print(json.dumps(classified, indent=2))

    assert classified["category"] == "RUNTIME_ERROR"
    assert classified["error_type"] == "ZeroDivisionError"
    print("\n[OK] Python Test PASSED cleanly!")

def test_invalid_path_graceful_handling():
    print("\n--------------------------------------------------")
    print("Testing Invalid Path Graceful Handling (None / Nonexistent)...")
    print("--------------------------------------------------")

    # Pass None to JavaAdapter
    adapter_none = JavaAdapter(None)
    analysis_none = adapter_none.analyze_project()
    print("JavaAdapter(None).analyze_project():", analysis_none)
    assert analysis_none["error"] == "Invalid or missing project path."

    res_none = adapter_none.run_tests()
    print("JavaAdapter(None).run_tests():", res_none["stderr"])

    # Pass None to PythonAdapter
    py_adapter_none = PythonAdapter(None)
    py_analysis_none = py_adapter_none.analyze_project()
    print("PythonAdapter(None).analyze_project():", py_analysis_none)
    assert py_analysis_none["error"] == "Invalid or missing project path."

    print("\n[OK] Invalid Path Graceful Handling PASSED cleanly!")

if __name__ == "__main__":
    test_java_single_file()
    test_python_single_file()
    test_invalid_path_graceful_handling()
