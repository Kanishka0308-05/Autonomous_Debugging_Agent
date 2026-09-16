import json
import re
from typing import Dict, Any
from utils.llm import call_gemini, is_gemini_available
from agents.bug_investigation.prompts import BUG_INVESTIGATION_SYSTEM_PROMPT, BUG_INVESTIGATION_USER_PROMPT

def fallback_bug_investigation(source_code: str, error_log: str, code_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Intelligent fallback bug investigation when LLM is unavailable.
    Parses stack traces and compilation logs to extract line numbers and error types.
    """
    functions = code_analysis.get("functions", [])
    suspected_fn = functions[0] if functions else "main"

    # Extract file name and line number from stack trace if present
    file_match = re.search(r'([A-Za-z0-9_\-\/\\]+\.(?:py|java)):(\d+)', error_log)
    if not file_match:
        file_match = re.search(r'File "([^"]+)", line (\d+)', error_log)
        
    suspected_file = file_match.group(1) if file_match else "source file"
    line_num = file_match.group(2) if file_match else "unknown"

    if line_num == "unknown":
        line_match = re.search(r'line (\d+)', error_log, re.IGNORECASE)
        line_num = line_match.group(1) if line_match else "unknown"

    # Extract suspicious snippet from code if possible
    suspicious_snippet = source_code.strip() if source_code else "See stack trace error location."
    if source_code:
        lines = source_code.splitlines()
        if line_num.isdigit() and int(line_num) <= len(lines):
            suspicious_snippet = lines[int(line_num) - 1].strip()

    reason = "Error detected in stack trace."
    if "NullPointerException" in error_log:
        reason = "NullPointerException occurs when attempting to call a method or access a field on an uninitialized (null) object reference."
    elif "ZeroDivisionError" in error_log or "/ by zero" in error_log:
        reason = "Division by zero occurs when denominator evaluates to 0 (e.g., empty collection or zero variable)."
    elif "IndexError" in error_log or "ArrayIndexOutOfBoundsException" in error_log:
        reason = "Attempting to access list or array index that does not exist."
    elif "TypeError" in error_log:
        reason = "Incompatible types used in operation."
    elif "KeyError" in error_log:
        reason = "Accessing dictionary key that does not exist in mapping."
    elif "compilation" in error_log.lower() or "cannot find symbol" in error_log.lower():
        reason = "Java compilation error encountered during build."

    return {
        "suspected_location": f"{suspected_file}:{line_num} in {suspected_fn}()",
        "suspicious_code": suspicious_snippet,
        "reason": reason,
        "confidence": "Medium (Fallback Analyzer)"
    }


def investigate_bug_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bug Investigation Agent Node for LangGraph.
    Receives source_code/project snippets, error_log, code_analysis, returns bug_investigation.
    """
    source_code = state.get("source_code", "")
    error_log = state.get("error_log", "")
    code_analysis = state.get("code_analysis", {})

    # In project mode, combine error logs or execution results if available
    exec_res = state.get("execution_result", {})
    if exec_res and not error_log:
        error_log = exec_res.get("stderr") or exec_res.get("output") or ""

    code_analysis_summary = code_analysis.get("summary", "Syntax valid")

    if is_gemini_available():
        user_prompt = BUG_INVESTIGATION_USER_PROMPT.format(
            source_code=source_code if source_code else f"Project snippets: {json.dumps(code_analysis.get('snippets', {}), indent=2)}",
            error_log=error_log,
            code_analysis_summary=code_analysis_summary
        )
        raw_response = call_gemini(user_prompt, BUG_INVESTIGATION_SYSTEM_PROMPT)
        
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
                return {"bug_investigation": parsed}
            except Exception:
                pass

    # Fallback mode
    result = fallback_bug_investigation(source_code, error_log, code_analysis)
    return {"bug_investigation": result}
