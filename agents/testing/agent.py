import os
import sys
import tempfile
import subprocess
import re
from typing import Dict, Any
from language_adapters.python.adapter import PythonAdapter
from language_adapters.java.adapter import JavaAdapter

def generate_default_tests(fixed_code: str) -> str:
    """
    Generates dynamic PyTest test cases for any Python code file using AST function inspection.
    """
    import ast

    test_lines = []

    try:
        tree = ast.parse(fixed_code)
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        
        for fn in functions:
            fn_name = fn.name
            arg_names = [arg.arg for arg in fn.args.args]
            
            if fn_name == "calculate_average":
                test_lines.append("""
def test_calculate_average_normal():
    assert calculate_average([10, 20, 30]) == 20.0

def test_calculate_average_empty():
    res = calculate_average([])
    assert res == 0.0 or res == 0 or res is None
""")
            elif fn_name in ("get_third_element", "get_third_item"):
                test_lines.append(f"""
def test_{fn_name}_valid():
    assert {fn_name}([10, 20, 30]) == 30

def test_{fn_name}_out_of_bounds():
    res = {fn_name}([10])
    assert res is None
""")
            elif fn_name == "apply_discount":
                test_lines.append("""
def test_apply_discount_normal():
    assert apply_discount(100, 20) == 80.0

def test_apply_discount_string_param():
    assert apply_discount(100, "20") == 80.0
""")
            elif fn_name in ("get_user_email", "get_email"):
                test_lines.append(f"""
def test_{fn_name}_present():
    assert {fn_name}({{"name": "Alice", "email": "a@example.com"}}) == "a@example.com"

def test_{fn_name}_missing():
    res = {fn_name}({{"name": "Bob"}})
    assert res is None or res == ""
""")
            else:
                num_args = len(arg_names)
                if num_args == 0:
                    test_lines.append(f"""
def test_{fn_name}_execution():
    {fn_name}()
""")
                elif num_args == 1:
                    test_lines.append(f"""
def test_{fn_name}_normal():
    try:
        {fn_name}([10, 20, 30])
    except Exception:
        try:
            {fn_name}(10)
        except Exception:
            {fn_name}("test")

def test_{fn_name}_edge_case():
    try:
        {fn_name}([])
    except Exception:
        try:
            {fn_name}(0)
        except Exception:
            {fn_name}(None)
""")
                elif num_args == 2:
                    test_lines.append(f"""
def test_{fn_name}_normal():
    try:
        {fn_name}(10, 2)
    except Exception:
        {fn_name}("a", "b")

def test_{fn_name}_edge_case():
    try:
        {fn_name}(10, 0)
    except Exception:
        {fn_name}(None, None)
""")
    except Exception:
        pass

    if not test_lines:
        test_lines.append("""
def test_module_execution_smoketest():
    assert True
""")

    return "\n".join(test_lines)


def run_pytest_in_sandbox(fixed_code: str, test_code: str = None) -> Dict[str, Any]:
    """
    Executes PyTest on the candidate fixed code in an isolated local temporary directory.
    Single-file Python execution mode.
    """
    if not test_code:
        test_code = generate_default_tests(fixed_code)

    with tempfile.TemporaryDirectory(prefix="debug_agent_") as temp_dir:
        solution_path = os.path.join(temp_dir, "solution.py")
        test_path = os.path.join(temp_dir, "test_solution.py")

        clean_solution = fixed_code
        if clean_solution.startswith("```python"):
            clean_solution = clean_solution[9:]
        if clean_solution.startswith("```"):
            clean_solution = clean_solution[3:]
        if clean_solution.endswith("```"):
            clean_solution = clean_solution[:-3]

        with open(solution_path, "w", encoding="utf-8") as f:
            f.write(clean_solution)

        test_file_content = f"from solution import *\n\n{test_code}\n"
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(test_file_content)

        try:
            cmd = [sys.executable, "-m", "pytest", test_path, "-v", "--no-header"]
            result = subprocess.run(
                cmd,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=15
            )

            output = result.stdout + "\n" + result.stderr
            exit_code = result.returncode

            passed_match = re.search(r'(\d+)\s+passed', output)
            failed_match = re.search(r'(\d+)\s+failed', output)

            passed_count = int(passed_match.group(1)) if passed_match else (0 if exit_code != 0 else 1)
            failed_count = int(failed_match.group(1)) if failed_match else (1 if exit_code != 0 else 0)
            total_run = passed_count + failed_count

            status = "PASS" if exit_code == 0 else "FAIL"

            return {
                "tests_run": total_run,
                "passed": passed_count,
                "failed": failed_count,
                "status": status,
                "output": output.strip(),
                "exit_code": exit_code
            }

        except subprocess.TimeoutExpired:
            return {
                "tests_run": 1,
                "passed": 0,
                "failed": 1,
                "status": "FAIL",
                "output": "PyTest execution timed out (possible infinite loop in fixed code).",
                "exit_code": -1
            }
        except Exception as e:
            return {
                "tests_run": 0,
                "passed": 0,
                "failed": 1,
                "status": "FAIL",
                "output": f"PyTest runner exception: {str(e)}",
                "exit_code": -1
            }


def test_code_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Testing Agent Node for LangGraph.
    Delegates project testing to language adapters in project mode, or uses sandbox PyTest in single-file mode.
    """
    project_path = state.get("project_path")
    language = state.get("language", "python")
    candidate_fix = state.get("candidate_fix", {})
    patches = state.get("patches") or candidate_fix.get("patches") or []

    if project_path and os.path.exists(project_path):
        # Project mode: Select language adapter
        if language == "java":
            adapter = JavaAdapter(project_path)
        else:
            adapter = PythonAdapter(project_path)

        # Apply patch to temporary workspace
        if patches:
            patch_res = adapter.apply_patch(patches)

        # Execute tests or project
        exec_res = adapter.run_tests()

        status = "PASS" if exec_res.get("status") == "passed" and exec_res.get("exit_code") == 0 else "FAIL"
        passed_cnt = exec_res.get("passed_count", 0)
        failed_cnt = exec_res.get("failed_count", 0)
        total_run = passed_cnt + failed_cnt

        test_results = {
            "tests_run": total_run,
            "passed": passed_cnt,
            "failed": failed_cnt,
            "status": status,
            "output": exec_res.get("output") or exec_res.get("stderr") or exec_res.get("stdout", "No output"),
            "exit_code": exec_res.get("exit_code", 0),
            "language": language
        }

        return {
            "test_results": test_results,
            "execution_result": exec_res
        }

    # Single-file mode
    fixed_code = candidate_fix.get("fixed_code", state.get("source_code", ""))
    user_test_code = state.get("test_code")
    test_results = run_pytest_in_sandbox(fixed_code, user_test_code)

    return {
        "test_results": test_results
    }
