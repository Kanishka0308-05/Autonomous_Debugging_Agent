import json
import re
from typing import Dict, Any
from utils.llm import call_gemini, is_gemini_available
from agents.bug_investigation.prompts import BUG_INVESTIGATION_SYSTEM_PROMPT, BUG_INVESTIGATION_USER_PROMPT

def fallback_bug_investigation(source_code: str, error_log: str, code_analysis: Dict[str, Any], classified_error: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Intelligent fallback bug investigation when LLM is unavailable.
    Parses stack traces, compilation logs, or classified error details to extract line numbers and code snippets.
    """
    classified_error = classified_error or {}
    functions = code_analysis.get("functions", [])
    suspected_fn = functions[0] if functions else "main"

    # Line number and file from classifier or stack trace
    line_num = str(classified_error.get("line_number")) if classified_error.get("line_number") is not None else "unknown"
    suspected_file = classified_error.get("file_name")

    if not suspected_file or line_num == "unknown":
        file_match = re.search(r'([A-Za-z0-9_\-\/\\]+\.(?:py|java)):(\d+)', error_log)
        if not file_match:
            file_match = re.search(r'File "([^"]+)", line (\d+)', error_log)
            
        src_files = code_analysis.get("source_files", [])
        default_file = src_files[0] if src_files else "source file"
        if not suspected_file:
            suspected_file = file_match.group(1) if file_match else default_file
        if line_num == "unknown":
            line_num = file_match.group(2) if file_match else "unknown"

    if line_num == "unknown":
        line_match = re.search(r'line (\d+)', error_log, re.IGNORECASE)
        line_num = line_match.group(1) if line_match else "unknown"

    # Extract suspicious snippet from code if possible
    suspicious_snippet = source_code.strip() if source_code else "See error location."
    if source_code:
        lines = source_code.splitlines()
        if line_num.isdigit() and 1 <= int(line_num) <= len(lines):
            suspicious_snippet = lines[int(line_num) - 1].strip()

    reason = classified_error.get("message") or "Error detected during execution."
    if classified_error.get("category"):
        reason = f"Classified Error [{classified_error.get('category')} - {classified_error.get('error_type')}]: {classified_error.get('message', reason)}"

    return {
        "suspected_location": f"{suspected_file}:{line_num} in {suspected_fn}()",
        "suspicious_code": suspicious_snippet,
        "reason": reason,
        "confidence": classified_error.get("confidence", "Medium (Classifier Engine)")
    }


def investigate_bug_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bug Investigation Agent Node for LangGraph.
    Receives source_code/project snippets, error_log, code_analysis, classified_error, returns bug_investigation.
    """
    source_code = state.get("source_code", "")
    error_log = state.get("error_log", "")
    code_analysis = state.get("code_analysis", {})
    classified_error = state.get("classified_error", {})

    # In project mode, combine error logs or execution results if available
    exec_res = state.get("execution_result", {})
    if exec_res and not error_log:
        error_log = exec_res.get("stderr") or exec_res.get("output") or ""

    code_analysis_summary = code_analysis.get("summary", "Syntax valid")

    if is_gemini_available():
        error_context = f"ERROR LOG:\n{error_log}"
        if classified_error:
            error_context += f"\n\nSTRUCTURED ERROR CLASSIFICATION:\n{json.dumps(classified_error, indent=2)}"

        user_prompt = BUG_INVESTIGATION_USER_PROMPT.format(
            source_code=source_code if source_code else f"Project snippets: {json.dumps(code_analysis.get('snippets', {}), indent=2)}",
            error_log=error_context,
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
    result = fallback_bug_investigation(source_code, error_log, code_analysis, classified_error)
    return {"bug_investigation": result}
