import json
from typing import Dict, Any
from utils.llm import call_gemini, is_gemini_available
from agents.root_cause.prompts import ROOT_CAUSE_SYSTEM_PROMPT, ROOT_CAUSE_USER_PROMPT

def fallback_root_cause(error_log: str, bug_investigation: Dict[str, Any], classified_error: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Fallback root cause analyzer when Gemini LLM is unavailable.
    Utilizes structured classified error details when present.
    """
    classified_error = classified_error or {}
    category = classified_error.get("category") or "RuntimeError"
    err_type = classified_error.get("error_type", "")
    
    if "NullPointerException" in error_log or err_type == "NullPointerException":
        category = classified_error.get("category") or "NullPointerException"
        cause = "The code attempts to invoke a method or dereference an attribute on a null object reference."
        explanation = "A variable or method parameter was not properly initialized or validated before accessing its methods/properties."
        strategy = "Add a null check guard (e.g., `if (obj != null)`) or assign a non-null fallback value before invocation."
    elif "ZeroDivisionError" in error_log or "/ by zero" in error_log or err_type == "ZeroDivisionError":
        category = classified_error.get("category") or "ZeroDivisionError"
        cause = "The code attempts to perform mathematical division where denominator evaluates to 0 without pre-checking collection length or variable value."
        explanation = "When an empty collection `[]` or 0 denominator is passed, dividing triggers a ZeroDivisionError."
        strategy = "Add a guard condition checking if denominator/length is 0 before dividing, returning 0 or default."
    elif "IndexError" in error_log or "ArrayIndexOutOfBoundsException" in error_log or err_type in ("IndexError", "ArrayIndexOutOfBoundsException"):
        category = classified_error.get("category") or "IndexError"
        cause = "The code accesses an array offset beyond the length of the list/array."
        explanation = "Accessing an out of range index raises an index boundary exception."
        strategy = "Validate index bound using `if (index < length)` check before indexing."
    elif "TypeError" in error_log or err_type == "TypeError":
        category = classified_error.get("category") or "TypeError"
        cause = "Incompatible type passed to arithmetic operator or function."
        explanation = "Attempting operation on incompatible types raises a TypeError."
        strategy = "Cast or convert parameters to appropriate types before performing operations."
    elif "KeyError" in error_log or err_type == "KeyError":
        category = classified_error.get("category") or "KeyError"
        cause = "Accessing dictionary key without checking key existence."
        explanation = "Accessing `dict[key]` directly raises KeyError when key is missing."
        strategy = "Use `dict.get(key, default)` or `if key in dict:` guard."
    elif "NameError" in error_log or err_type == "NameError":
        category = classified_error.get("category") or "NameError"
        cause = "The code references a variable or symbol that has not been defined or initialized in current scope."
        explanation = "Referencing an unassigned identifier raises a NameError at runtime."
        strategy = "Define or initialize the variable before usage, or fix identifier spelling."
    elif "SyntaxError" in error_log or err_type == "SyntaxError":
        category = classified_error.get("category") or "SyntaxError"
        cause = "Python parser encountered invalid syntax structure."
        explanation = "Code contains missing punctuation, invalid indentation, or incomplete expressions."
        strategy = "Correct syntax errors (e.g., add missing colons or closing brackets)."
    elif classified_error.get("category") == "LOGICAL_ERROR":
        category = "LOGICAL_ERROR"
        cause = classified_error.get("message", "Logical code execution failure detected via test output.")
        explanation = classified_error.get("evidence", "Test assertion failure or output mismatch.")
        strategy = "Review function logic, calculation operators, and boundary conditions."
    elif "compilation" in error_log.lower() or "cannot find symbol" in error_log.lower():
        category = classified_error.get("category") or "CompilationError"
        cause = "Java compiler failed to compile source file."
        explanation = "Missing symbols, mismatched types, or invalid Java syntax preventing bytecode generation."
        strategy = "Resolve missing symbol imports, correct variable declarations, or fix syntax."
    else:
        cause = classified_error.get("message") or f"Exception encountered: {error_log.splitlines()[-1] if error_log else 'Unknown error'}"
        explanation = "The program failed due to missing validation or invalid operational state."
        strategy = "Add input validation and boundary checks."

    return {
        "root_cause": cause,
        "bug_category": category,
        "explanation": explanation,
        "recommended_fix_strategy": strategy
    }


def analyze_root_cause_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Root Cause Agent Node for LangGraph.
    Receives state with source_code, error_log, bug_investigation, classified_error.
    Returns root_cause dict.
    """
    source_code = state.get("source_code", "")
    error_log = state.get("error_log", "")
    bug_investigation = state.get("bug_investigation", {})
    classified_error = state.get("classified_error", {})

    exec_res = state.get("execution_result", {})
    if exec_res and not error_log:
        error_log = exec_res.get("stderr") or exec_res.get("output") or ""

    if is_gemini_available():
        error_ctx = f"ERROR LOG:\n{error_log}"
        if classified_error:
            error_ctx += f"\n\nCLASSIFIED ERROR DETAILS:\n{json.dumps(classified_error, indent=2)}"

        user_prompt = ROOT_CAUSE_USER_PROMPT.format(
            source_code=source_code if source_code else f"Project code context",
            error_log=error_ctx,
            bug_investigation=json.dumps(bug_investigation, indent=2)
        )
        raw_response = call_gemini(user_prompt, ROOT_CAUSE_SYSTEM_PROMPT)

        if raw_response:
            try:
                cleaned = raw_response.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                
                parsed = json.loads(cleaned.strip())
                return {"root_cause": parsed}
            except Exception:
                pass

    # Fallback mode
    result = fallback_root_cause(error_log, bug_investigation, classified_error)
    return {"root_cause": result}
