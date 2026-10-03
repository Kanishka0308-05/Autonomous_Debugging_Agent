import json
from typing import Dict, Any
from utils.llm import call_llm, is_llm_available
from agents.verification.prompts import VERIFICATION_SYSTEM_PROMPT, VERIFICATION_USER_PROMPT


def evaluate_verification_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verification Agent Node for LangGraph.
    Receives original error, root cause, candidate fix, and test results.
    Determines whether the fix is VERIFIED or FAILED.
    """
    error_log = state.get("error_log", "")
    root_cause = state.get("root_cause", {})
    candidate_fix = state.get("candidate_fix", {})
    test_results = state.get("test_results", {})

    test_status = test_results.get("status", "FAIL")
    failed_count = test_results.get("failed", 0)
    exit_code = test_results.get("exit_code", 0)
    output = test_results.get("output", "")

    has_error_in_output = any(err_kw in output for err_kw in [
        "Traceback (most recent call last):", "SyntaxError:", "IndentationError:",
        "TypeError:", "ValueError:", "ZeroDivisionError:", "IndexError:",
        "KeyError:", "AttributeError:", "Compilation failed"
    ])

    # Base rule-based decision
    if test_status == "PASS" and failed_count == 0 and exit_code == 0 and not has_error_in_output:
        verified = True
        status = "VERIFIED"
        default_reason = "All automated unit tests/builds passed cleanly and the original error condition was eliminated."
    else:
        verified = False
        status = "FAILED"
        default_reason = f"Execution failed ({failed_count} test/build error(s), exit code {exit_code}). Output: {output[:200]}"

    # LLM reasoning enhancement if available
    if is_llm_available():
        user_prompt = VERIFICATION_USER_PROMPT.format(
            error_log=error_log,
            root_cause=json.dumps(root_cause, indent=2),
            candidate_fix=json.dumps(candidate_fix, indent=2),
            test_results=json.dumps(test_results, indent=2)
        )
        raw_response = call_llm(user_prompt, VERIFICATION_SYSTEM_PROMPT)


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
                if "verified" in parsed and "status" in parsed:
                    # Enforce consistency with actual test results
                    if test_status == "FAIL" or failed_count > 0 or exit_code != 0 or has_error_in_output:
                        parsed["verified"] = False
                        parsed["status"] = "FAILED"
                    return {"verification_result": parsed}
            except Exception:
                pass

    # Fallback / Direct result
    result = {
        "verified": verified,
        "status": status,
        "reason": default_reason
    }

    return {
        "verification_result": result
    }
