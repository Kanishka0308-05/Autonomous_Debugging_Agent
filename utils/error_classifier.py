import re
import os
import ast
from typing import Dict, Any, Optional
from utils.error_patterns import (
    CATEGORY_SYNTAX_ERROR,
    CATEGORY_COMPILE_ERROR,
    CATEGORY_TYPE_ERROR,
    CATEGORY_NAME_ERROR,
    CATEGORY_RUNTIME_ERROR,
    CATEGORY_IMPORT_ERROR,
    CATEGORY_FILE_IO_ERROR,
    CATEGORY_DEPENDENCY_ERROR,
    CATEGORY_TEST_FAILURE,
    CATEGORY_LOGICAL_ERROR,
    CATEGORY_OTHER_RUNTIME,
    CATEGORY_OTHER_COMPILE,
    CATEGORY_UNKNOWN,
    SOURCE_STATIC_ANALYSIS,
    SOURCE_COMPILER,
    SOURCE_RUNTIME,
    SOURCE_TEST,
    SOURCE_DEPENDENCY,
    SOURCE_UNKNOWN,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
    SEVERITY_NONE,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
    PYTHON_ERROR_MAP,
    JAVA_RUNTIME_MAP,
    JAVA_COMPILER_PATTERNS
)

def classify_error(
    language: str,
    source_code: str,
    execution_result: Optional[Dict[str, Any]] = None,
    error_log: str = "",
    test_results: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Error Classification Engine.
    Analyzes execution outputs, compiler logs, tracebacks, and source code to produce
    a structured error classification object.
    """
    lang = (language or "Python").strip().capitalize()
    execution_result = execution_result or {}
    test_results = test_results or {}
    combined_log = (error_log + "\n" + execution_result.get("output", "") + "\n" + execution_result.get("stderr", "")).strip()

    # Default Structured Object
    result = {
        "language": lang,
        "category": CATEGORY_UNKNOWN,
        "error_type": "UnknownError",
        "subtype": "UNCLASSIFIED",
        "severity": SEVERITY_MEDIUM,
        "line_number": None,
        "message": "No detailed error message extracted.",
        "source": SOURCE_UNKNOWN,
        "confidence": CONFIDENCE_LOW,
        "evidence": "",
        "confirmed": False,
        "file_name": None,
        "stack_trace": combined_log if combined_log else None,
        "expected": None,
        "actual": None,
        "test_name": None
    }

    # 1. Check for Clean Execution / No Error
    exit_code = execution_result.get("exit_code", 0)
    status = execution_result.get("status", "passed")
    stderr = execution_result.get("stderr", "").strip()
    tests_run = test_results.get("tests_run", 0) or execution_result.get("tests_run", False)
    failed_tests = test_results.get("failed", 0) if test_results else execution_result.get("failed_count", 0)

    # Check if there is no error at all
    no_compilation_err = not bool(re.search(r'error:|Exception|Traceback', combined_log, re.IGNORECASE))
    if exit_code == 0 and status == "passed" and not stderr and failed_tests == 0 and no_compilation_err:
        result.update({
            "category": "NO_ERROR",
            "error_type": "None",
            "subtype": "CLEAN_EXECUTION",
            "severity": SEVERITY_NONE,
            "message": "No compilation, runtime, or test errors detected.",
            "source": SOURCE_RUNTIME if lang == "Python" else SOURCE_COMPILER,
            "confidence": CONFIDENCE_HIGH,
            "confirmed": False,
            "evidence": "Execution completed cleanly with exit code 0."
        })

        # Static analysis sanity check for potential unconfirmed issues
        possible_issue = _detect_static_possible_issues(lang, source_code)
        if possible_issue:
            result["category"] = "POSSIBLE_ISSUE"
            result["message"] = f"Code runs cleanly, but potential issue noted: {possible_issue['message']}"
            result["subtype"] = possible_issue["subtype"]
            result["severity"] = SEVERITY_LOW
            result["evidence"] = possible_issue["evidence"]

        return result

    # 2. Python Classification
    if lang == "Python":
        return _classify_python_error(source_code, execution_result, combined_log, test_results, result)

    # 3. Java Classification
    elif lang == "Java":
        return _classify_java_error(source_code, execution_result, combined_log, test_results, result)

    return result


def _classify_python_error(
    source_code: str,
    exec_res: Dict[str, Any],
    combined_log: str,
    test_res: Dict[str, Any],
    base_result: Dict[str, Any]
) -> Dict[str, Any]:
    res = dict(base_result)

    # A. Check for SyntaxError / IndentationError in AST / Compile
    try:
        if source_code:
            ast.parse(source_code)
    except SyntaxError as e:
        res.update({
            "category": CATEGORY_SYNTAX_ERROR,
            "error_type": type(e).__name__,
            "subtype": "INDENTATION_ERROR" if isinstance(e, IndentationError) else "INVALID_SYNTAX",
            "severity": SEVERITY_HIGH,
            "line_number": e.lineno,
            "message": e.msg,
            "source": SOURCE_STATIC_ANALYSIS,
            "confidence": CONFIDENCE_HIGH,
            "evidence": f"SyntaxError at line {e.lineno}: {e.msg}",
            "confirmed": True
        })
        return res

    # B. Check Traceback Output
    line_match = re.search(r'File "([^"]+)", line (\d+)', combined_log)
    if line_match:
        res["file_name"] = line_match.group(1)
        res["line_number"] = int(line_match.group(2))

    # Match Exception Class and Message (e.g. ZeroDivisionError: division by zero)
    exc_match = re.search(r'([A-Za-z_][A-Za-z0-9_]*Error|[A-Za-z_][A-Za-z0-9_]*Exception):\s*(.*)', combined_log)
    if exc_match:
        err_type = exc_match.group(1).strip()
        err_msg = exc_match.group(2).strip()

        res["error_type"] = err_type
        res["message"] = err_msg if err_msg else f"Raised {err_type}"
        res["evidence"] = exc_match.group(0)
        res["confirmed"] = True

        if err_type in PYTHON_ERROR_MAP:
            mapping = PYTHON_ERROR_MAP[err_type]
            res.update({
                "category": mapping["category"],
                "subtype": mapping["subtype"],
                "severity": mapping["severity"],
                "source": mapping["source"],
                "confidence": CONFIDENCE_HIGH
            })
        else:
            # Generic Python Error Fallback
            res.update({
                "category": CATEGORY_OTHER_RUNTIME,
                "subtype": "GENERIC_PYTHON_EXCEPTION",
                "severity": SEVERITY_HIGH,
                "source": SOURCE_RUNTIME,
                "confidence": CONFIDENCE_MEDIUM
            })
        return res

    # C. Check for Test Failures / Logical Errors
    failed_tests = test_res.get("failed", 0) or exec_res.get("failed_count", 0)
    if failed_tests > 0 or "FAIL" in exec_res.get("output", "") or "assert " in combined_log:
        logical_info = _detect_logical_error(source_code, combined_log)
        res.update({
            "category": CATEGORY_LOGICAL_ERROR if logical_info else CATEGORY_TEST_FAILURE,
            "error_type": "AssertionError" if "assert " in combined_log else "TestFailure",
            "subtype": logical_info["subtype"] if logical_info else "INCORRECT_OUTPUT",
            "severity": SEVERITY_MEDIUM,
            "source": SOURCE_TEST,
            "confidence": CONFIDENCE_HIGH,
            "evidence": logical_info["evidence"] if logical_info else "Test assertion or output check failed.",
            "confirmed": True,
            "message": logical_info["message"] if logical_info else "Test suite failed."
        })
        return res

    # D. Unknown / Unparsed Error
    if combined_log:
        res.update({
            "category": CATEGORY_OTHER_RUNTIME,
            "error_type": "RuntimeFailure",
            "severity": SEVERITY_HIGH,
            "source": SOURCE_RUNTIME,
            "confidence": CONFIDENCE_MEDIUM,
            "evidence": combined_log[:300],
            "confirmed": True
        })

    return res


def _classify_java_error(
    source_code: str,
    exec_res: Dict[str, Any],
    combined_log: str,
    test_res: Dict[str, Any],
    base_result: Dict[str, Any]
) -> Dict[str, Any]:
    res = dict(base_result)

    # A. Check Compiler Errors (from javac or Maven build)
    comp_match = re.search(r'([A-Za-z0-9_\-\/\\]+\.java):(\d+):\s*error:\s*(.*)', combined_log)
    if comp_match or "compilation" in combined_log.lower() or "error:" in combined_log.lower():
        file_n = comp_match.group(1) if comp_match else None
        line_n = int(comp_match.group(2)) if comp_match else None
        msg = comp_match.group(3) if comp_match else "Java compilation error"

        res.update({
            "category": CATEGORY_COMPILE_ERROR,
            "error_type": "JavaCompilerError",
            "subtype": "COMPILATION_FAILURE",
            "severity": SEVERITY_HIGH,
            "line_number": line_n,
            "file_name": file_n,
            "message": msg,
            "source": SOURCE_COMPILER,
            "confidence": CONFIDENCE_HIGH,
            "evidence": comp_match.group(0) if comp_match else combined_log[:200],
            "confirmed": True
        })

        # Match specific compiler patterns
        for pattern, cat, sub, sev in JAVA_COMPILER_PATTERNS:
            if re.search(pattern, combined_log, re.IGNORECASE):
                res["category"] = cat
                res["subtype"] = sub
                res["severity"] = sev
                break

        return res

    # B. Check Runtime Exceptions (e.g. NullPointerException, ArithmeticException)
    line_match = re.search(r'at\s+[\w\.]+\(([A-Za-z0-9_\$]+\.java):(\d+)\)', combined_log)
    if line_match:
        res["file_name"] = line_match.group(1)
        res["line_number"] = int(line_match.group(2))

    exc_match = re.search(r'([a-zA-Z0-9\.]+(?:Exception|Error)):?\s*(.*)', combined_log)
    if exc_match:
        full_exc_name = exc_match.group(1).strip()
        short_exc_name = full_exc_name.split('.')[-1]
        msg = exc_match.group(2).strip()

        res["error_type"] = short_exc_name
        res["message"] = msg if msg else f"Thrown {short_exc_name}"
        res["evidence"] = exc_match.group(0)
        res["confirmed"] = True

        if short_exc_name in JAVA_RUNTIME_MAP:
            mapping = JAVA_RUNTIME_MAP[short_exc_name]
            res.update({
                "category": mapping["category"],
                "subtype": mapping["subtype"],
                "severity": mapping["severity"],
                "source": mapping["source"],
                "confidence": CONFIDENCE_HIGH
            })
        else:
            res.update({
                "category": CATEGORY_OTHER_RUNTIME,
                "subtype": "GENERIC_JAVA_EXCEPTION",
                "severity": SEVERITY_HIGH,
                "source": SOURCE_RUNTIME,
                "confidence": CONFIDENCE_MEDIUM
            })
        return res

    # C. Check Java Test Failures / Logical Errors
    failed_tests = test_res.get("failed", 0) or exec_res.get("failed_count", 0)
    if failed_tests > 0 or "Tests run:" in combined_log:
        res.update({
            "category": CATEGORY_TEST_FAILURE,
            "error_type": "JavaTestFailure",
            "subtype": "TEST_ASSERTION_FAILED",
            "severity": SEVERITY_MEDIUM,
            "source": SOURCE_TEST,
            "confidence": CONFIDENCE_HIGH,
            "evidence": combined_log[:300],
            "confirmed": True,
            "message": f"{failed_tests} Java unit test(s) failed."
        })
        return res

    # D. Generic Fallback
    if combined_log:
        res.update({
            "category": CATEGORY_OTHER_RUNTIME,
            "error_type": "JavaExecutionFailure",
            "severity": SEVERITY_HIGH,
            "source": SOURCE_RUNTIME,
            "confidence": CONFIDENCE_MEDIUM,
            "evidence": combined_log[:300],
            "confirmed": True
        })

    return res


def _detect_logical_error(source_code: str, log_or_output: str) -> Optional[Dict[str, Any]]:
    """
    Detects logical bug patterns in code / test outputs (e.g. incorrect return value, off-by-one, wrong operator).
    """
    if not source_code:
        return None

    # Check wrong calculation pattern (e.g., def add(a, b): return a - b)
    if re.search(r'def\s+(?:add|sum|total)\s*\([^)]*\):\s*\n\s*return\s+\w+\s*-\s*\w+', source_code):
        return {
            "subtype": "INCORRECT_RETURN_VALUE",
            "message": "Logical Bug: Subtraction operator used in addition function.",
            "evidence": "Operator '-' used inside add/sum function."
        }

    # Check off-by-one loop pattern (e.g. range(len(arr) - 1))
    if re.search(r'range\s*\(\s*len\s*\([^)]+\)\s*-\s*1\s*\)', source_code):
        return {
            "subtype": "OFF_BY_ONE",
            "message": "Logical Bug: Loop excludes last element (potential off-by-one boundary truncation).",
            "evidence": "range(len(...) - 1) truncates final iteration."
        }

    # Check incorrect condition pattern (e.g. > 18 vs >= 18)
    if re.search(r'if\s+age\s*>\s*18', source_code) and "18" in log_or_output:
        return {
            "subtype": "INCORRECT_CONDITION",
            "message": "Logical Bug: Strict inequality (> 18) excludes boundary value 18.",
            "evidence": "Strict '>' operator excludes edge boundary condition."
        }

    return None


def _detect_static_possible_issues(language: str, source_code: str) -> Optional[Dict[str, Any]]:
    """
    Static analysis check for code that executes cleanly but contains possible code smells.
    Returns POSSIBLE_ISSUE dict with confirmed=False.
    """
    if not source_code:
        return None

    if language.lower() == "python":
        # Unused variable / broad except clause
        if re.search(r'except\s*:\s*\n\s*pass', source_code):
            return {
                "subtype": "SILENT_EXCEPTION_SWALLOWING",
                "message": "Broad 'except: pass' silently suppresses all exceptions.",
                "evidence": "Bare 'except: pass' block detected."
            }

    elif language.lower() == "java":
        if re.search(r'catch\s*\(\s*Exception\s+\w+\s*\)\s*\{\s*\}', source_code):
            return {
                "subtype": "SILENT_EXCEPTION_SWALLOWING",
                "message": "Empty catch (Exception e) block swallows errors silently.",
                "evidence": "Empty catch block detected."
            }

    return None
