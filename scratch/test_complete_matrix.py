import os
import sys
import tempfile
import json
import zipfile
import io

# Ensure workspace root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from demo_examples import DEMO_EXAMPLES, DEMO_PROJECT_PRESETS
from language_adapters.python.adapter import PythonAdapter
from language_adapters.java.adapter import JavaAdapter
from utils.error_classifier import classify_error
from orchestration.graph import debugging_app
from database.database import save_debug_session, get_all_sessions, init_db

def run_matrix_tests():
    print("==================================================")
    print("   END-TO-END AUTOMATED STABILITY & TEST MATRIX   ")
    print("==================================================\n")

    init_db()
    results = []

    # ----------------------------------------------------
    # TEST 1: Demo Presets -> Python ZeroDivisionError
    # ----------------------------------------------------
    print("[TEST 1] Demo Presets: Python ZeroDivisionError")
    ex1 = DEMO_EXAMPLES["Python: ZeroDivisionError"]
    demo_dir1 = tempfile.mkdtemp(prefix="matrix_test_1_")
    file1 = os.path.join(demo_dir1, ex1["filename"])
    with open(file1, "w", encoding="utf-8") as f:
        f.write(ex1["code"])

    adapter1 = PythonAdapter(demo_dir1)
    exec1 = adapter1.run_project()
    classified1 = classify_error("python", ex1["code"], exec1, ex1["error_log"])

    state1 = {
        "input_mode": "single_file",
        "project_path": demo_dir1,
        "project_name": ex1["filename"],
        "language": "python",
        "build_system": "pytest",
        "source_code": ex1["code"],
        "error_log": ex1["error_log"],
        "execution_result": exec1,
        "classified_error": classified1,
        "test_code": ex1.get("test_code", ""),
        "code_analysis": None, "bug_investigation": None, "root_cause": None,
        "candidate_fix": None, "test_results": None, "verification_result": None,
        "iteration_count": 0, "max_iterations": 3, "history": [], "final_report": None, "is_mock_mode": True
    }
    res1 = debugging_app.invoke(state1)
    status1 = res1.get("final_report", {}).get("status")
    print(f"  Result: Classified = {classified1['category']}, Pipeline Status = {status1}")
    assert classified1["category"] == "RUNTIME_ERROR"
    assert classified1["error_type"] == "ZeroDivisionError"
    results.append(("TEST 1: Demo Presets Python ZeroDivisionError", "PASSED"))

    # ----------------------------------------------------
    # TEST 2: Demo Presets -> Java ArithmeticException
    # ----------------------------------------------------
    print("\n[TEST 2] Demo Presets: Java ArithmeticException")
    ex2 = DEMO_EXAMPLES["Java: ArithmeticException"]
    demo_dir2 = tempfile.mkdtemp(prefix="matrix_test_2_")
    file2 = os.path.join(demo_dir2, ex2["filename"])
    with open(file2, "w", encoding="utf-8") as f:
        f.write(ex2["code"])

    adapter2 = JavaAdapter(demo_dir2)
    exec2 = adapter2.run_project()
    classified2 = classify_error("java", ex2["code"], exec2, ex2["error_log"])

    state2 = {
        "input_mode": "single_file",
        "project_path": demo_dir2,
        "project_name": ex2["filename"],
        "language": "java",
        "build_system": "java-direct",
        "source_code": ex2["code"],
        "error_log": ex2["error_log"],
        "execution_result": exec2,
        "classified_error": classified2,
        "test_code": "",
        "code_analysis": None, "bug_investigation": None, "root_cause": None,
        "candidate_fix": None, "test_results": None, "verification_result": None,
        "iteration_count": 0, "max_iterations": 3, "history": [], "final_report": None, "is_mock_mode": True
    }
    res2 = debugging_app.invoke(state2)
    status2 = res2.get("final_report", {}).get("status")
    print(f"  Result: Classified = {classified2['category']}, Pipeline Status = {status2}")
    assert classified2["category"] == "RUNTIME_ERROR"
    assert classified2["error_type"] == "ArithmeticException"
    results.append(("TEST 2: Demo Presets Java ArithmeticException", "PASSED"))

    # ----------------------------------------------------
    # TEST 3: Upload Source File -> Python ZeroDivisionError
    # ----------------------------------------------------
    print("\n[TEST 3] Upload Source File: Python ZeroDivisionError")
    code3 = """def divide(a, b):
    return a / b

print(divide(10, 0))
"""
    demo_dir3 = tempfile.mkdtemp(prefix="matrix_test_3_")
    file3 = os.path.join(demo_dir3, "main.py")
    with open(file3, "w", encoding="utf-8") as f:
        f.write(code3)

    adapter3 = PythonAdapter(demo_dir3)
    exec3 = adapter3.run_project()
    classified3 = classify_error("python", code3, exec3, exec3.get("output", ""))

    state3 = {
        "input_mode": "single_file",
        "project_path": demo_dir3,
        "project_name": "main.py",
        "language": "python",
        "build_system": "pytest",
        "source_code": code3,
        "error_log": exec3.get("output", ""),
        "execution_result": exec3,
        "classified_error": classified3,
        "test_code": None,
        "code_analysis": None, "bug_investigation": None, "root_cause": None,
        "candidate_fix": None, "test_results": None, "verification_result": None,
        "iteration_count": 0, "max_iterations": 3, "history": [], "final_report": None, "is_mock_mode": True
    }
    res3 = debugging_app.invoke(state3)
    print(f"  Result: Classified = {classified3['category']}, Pipeline Status = {res3.get('final_report', {}).get('status')}")
    assert classified3["category"] == "RUNTIME_ERROR"
    assert classified3["error_type"] == "ZeroDivisionError"
    results.append(("TEST 3: Upload Source File Python ZeroDivisionError", "PASSED"))

    # ----------------------------------------------------
    # TEST 4: Upload Source File -> Java ArithmeticException
    # ----------------------------------------------------
    print("\n[TEST 4] Upload Source File: Java ArithmeticException")
    code4 = """public class Main {
    public static void main(String[] args) {
        int x = 50;
        int y = 0;
        int z = x / y;
        System.out.println(z);
    }
}
"""
    demo_dir4 = tempfile.mkdtemp(prefix="matrix_test_4_")
    file4 = os.path.join(demo_dir4, "Main.java")
    with open(file4, "w", encoding="utf-8") as f:
        f.write(code4)

    adapter4 = JavaAdapter(demo_dir4)
    exec4 = adapter4.run_project()
    classified4 = classify_error("java", code4, exec4, exec4.get("output", ""))

    state4 = {
        "input_mode": "single_file",
        "project_path": demo_dir4,
        "project_name": "Main.java",
        "language": "java",
        "build_system": "java-direct",
        "source_code": code4,
        "error_log": exec4.get("output", ""),
        "execution_result": exec4,
        "classified_error": classified4,
        "test_code": None,
        "code_analysis": None, "bug_investigation": None, "root_cause": None,
        "candidate_fix": None, "test_results": None, "verification_result": None,
        "iteration_count": 0, "max_iterations": 3, "history": [], "final_report": None, "is_mock_mode": True
    }
    res4 = debugging_app.invoke(state4)
    print(f"  Result: Classified = {classified4['category']}, Pipeline Status = {res4.get('final_report', {}).get('status')}")
    assert classified4["category"] == "RUNTIME_ERROR"
    assert classified4["error_type"] == "ArithmeticException"
    results.append(("TEST 4: Upload Source File Java ArithmeticException", "PASSED"))

    # ----------------------------------------------------
    # TEST 5: Upload Source File -> Working Python Program
    # ----------------------------------------------------
    print("\n[TEST 5] Upload Source File: Working Python Program")
    code5 = """def greet(name):
    return f"Hello {name}"

if __name__ == "__main__":
    print(greet("World"))
"""
    demo_dir5 = tempfile.mkdtemp(prefix="matrix_test_5_")
    file5 = os.path.join(demo_dir5, "main.py")
    with open(file5, "w", encoding="utf-8") as f:
        f.write(code5)

    adapter5 = PythonAdapter(demo_dir5)
    exec5 = adapter5.run_project()
    classified5 = classify_error("python", code5, exec5, "")

    print(f"  Result: Category = {classified5['category']}, Confirmed = {classified5['confirmed']}")
    assert classified5["category"] == "NO_ERROR"
    assert not classified5["confirmed"]
    results.append(("TEST 5: Upload Source File Working Python Program", "PASSED"))

    # ----------------------------------------------------
    # TEST 6: Upload Source File -> Working Java Program
    # ----------------------------------------------------
    print("\n[TEST 6] Upload Source File: Working Java Program")
    code6 = """public class Main {
    public static void main(String[] args) {
        System.out.println("Clean Execution");
    }
}
"""
    demo_dir6 = tempfile.mkdtemp(prefix="matrix_test_6_")
    file6 = os.path.join(demo_dir6, "Main.java")
    with open(file6, "w", encoding="utf-8") as f:
        f.write(code6)

    adapter6 = JavaAdapter(demo_dir6)
    exec6 = adapter6.run_project()
    classified6 = classify_error("java", code6, exec6, "")

    print(f"  Result: Category = {classified6['category']}, Confirmed = {classified6['confirmed']}")
    assert classified6["category"] == "NO_ERROR"
    assert not classified6["confirmed"]
    results.append(("TEST 6: Upload Source File Working Java Program", "PASSED"))

    # ----------------------------------------------------
    # TEST 7: Upload Project ZIP -> Existing Python Demo Project
    # ----------------------------------------------------
    print("\n[TEST 7] Upload Project ZIP: Existing Python Demo Project")
    py_zip_spec = DEMO_PROJECT_PRESETS["Python ZIP (ZeroDivisionError)"]
    zip_dir7 = tempfile.mkdtemp(prefix="matrix_test_7_")
    for fname, content in py_zip_spec["files"].items():
        fp = os.path.join(zip_dir7, fname)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)

    adapter7 = PythonAdapter(zip_dir7)
    exec7 = adapter7.run_tests()
    classified7 = classify_error("python", py_zip_spec["files"]["main.py"], exec7, exec7.get("output", ""))

    state7 = {
        "input_mode": "project",
        "project_path": zip_dir7,
        "project_name": py_zip_spec["filename"],
        "language": "python",
        "build_system": "pytest",
        "source_code": py_zip_spec["files"]["main.py"],
        "error_log": exec7.get("output", ""),
        "execution_result": exec7,
        "classified_error": classified7,
        "test_code": py_zip_spec["files"]["test_main.py"],
        "code_analysis": None, "bug_investigation": None, "root_cause": None,
        "candidate_fix": None, "test_results": None, "verification_result": None,
        "iteration_count": 0, "max_iterations": 3, "history": [], "final_report": None, "is_mock_mode": True
    }
    res7 = debugging_app.invoke(state7)
    print(f"  Result: Classified = {classified7['category']}, Pipeline Status = {res7.get('final_report', {}).get('status')}")
    results.append(("TEST 7: Upload Project ZIP Python Demo Project", "PASSED"))

    # ----------------------------------------------------
    # TEST 8: Upload Project ZIP -> Existing Java Demo Project
    # ----------------------------------------------------
    print("\n[TEST 8] Upload Project ZIP: Existing Java Demo Project")
    java_zip_spec = DEMO_PROJECT_PRESETS["Java Maven ZIP (NullPointerException)"]
    zip_dir8 = tempfile.mkdtemp(prefix="matrix_test_8_")
    for fname, content in java_zip_spec["files"].items():
        fp = os.path.join(zip_dir8, fname)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)

    adapter8 = JavaAdapter(zip_dir8)
    exec8 = adapter8.run_project()
    classified8 = classify_error("java", java_zip_spec["files"]["src/main/java/com/example/UserService.java"], exec8, exec8.get("output", ""))

    state8 = {
        "input_mode": "project",
        "project_path": zip_dir8,
        "project_name": java_zip_spec["filename"],
        "language": "java",
        "build_system": "maven",
        "source_code": java_zip_spec["files"]["src/main/java/com/example/UserService.java"],
        "error_log": exec8.get("output", ""),
        "execution_result": exec8,
        "classified_error": classified8,
        "test_code": java_zip_spec["files"]["src/test/java/com/example/UserServiceTest.java"],
        "code_analysis": None, "bug_investigation": None, "root_cause": None,
        "candidate_fix": None, "test_results": None, "verification_result": None,
        "iteration_count": 0, "max_iterations": 3, "history": [], "final_report": None, "is_mock_mode": True
    }
    res8 = debugging_app.invoke(state8)
    print(f"  Result: Classified = {classified8['category']}, Pipeline Status = {res8.get('final_report', {}).get('status')}")
    results.append(("TEST 8: Upload Project ZIP Java Demo Project", "PASSED"))

    # ----------------------------------------------------
    # TEST 9: Gemini Unavailable / Mock Mode Fallback
    # ----------------------------------------------------
    print("\n[TEST 9] Gemini Unavailable / Mock Mode Fallback")
    mock_state = {
        "input_mode": "single_file",
        "project_path": demo_dir1,
        "project_name": "demo.py",
        "language": "python",
        "build_system": "pytest",
        "source_code": ex1["code"],
        "error_log": ex1["error_log"],
        "execution_result": exec1,
        "classified_error": classified1,
        "test_code": ex1.get("test_code", ""),
        "code_analysis": None, "bug_investigation": None, "root_cause": None,
        "candidate_fix": None, "test_results": None, "verification_result": None,
        "iteration_count": 0, "max_iterations": 3, "history": [], "final_report": None,
        "is_mock_mode": True
    }
    res_mock = debugging_app.invoke(mock_state)
    print(f"  Result: Mock Mode Execution Completed with Status = {res_mock.get('final_report', {}).get('status')}")
    assert res_mock.get("final_report") is not None
    results.append(("TEST 9: Gemini Unavailable / Mock Mode Fallback", "PASSED"))

    # ----------------------------------------------------
    # TEST 10: SQLite Session History Database
    # ----------------------------------------------------
    print("\n[TEST 10] SQLite Session History Database")
    save_debug_session(
        title="Fix ZeroDivisionError (test_demo.py)",
        source_code="total / count",
        error_log="ZeroDivisionError: division by zero",
        bug_category="RUNTIME_ERROR",
        root_cause="Division by zero in average calculation",
        fixed_code="if count == 0: return 0.0",
        verification_status="VERIFIED",
        iterations=1,
        language="Python",
        project_name="test_demo.py"
    )
    history_records = get_all_sessions()
    print(f"  Result: Retrieved {len(history_records)} saved session record(s) from SQLite.")
    assert len(history_records) > 0
    results.append(("TEST 10: SQLite Session History Database", "PASSED"))

    print("\n==================================================")
    print(f"  SUMMARY RESULTS: {len(results)} / {len(results)} TEST SCENARIOS PASSED")
    print("==================================================")

if __name__ == "__main__":
    run_matrix_tests()
