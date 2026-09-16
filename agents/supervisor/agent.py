from typing import Dict, Any, List

def supervisor_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Supervisor Agent Node for LangGraph.
    Tracks iteration counts, updates history, and prepares final summary report.
    """
    iteration_count = state.get("iteration_count", 0) + 1
    max_iterations = state.get("max_iterations", 3)
    history = state.get("history", [])

    verification_result = state.get("verification_result", {})
    verified = verification_result.get("verified", False)
    status = verification_result.get("status", "UNVERIFIED")

    candidate_fix = state.get("candidate_fix", {})
    test_results = state.get("test_results", {})

    # Record current iteration snapshot
    snapshot = {
        "iteration": iteration_count,
        "candidate_fix": candidate_fix.get("fixed_code"),
        "patches": candidate_fix.get("patches", []),
        "test_status": test_results.get("status"),
        "verified": verified,
        "verification_reason": verification_result.get("reason")
    }
    updated_history = history + [snapshot]

    # Generate final report summary
    final_report = {
        "summary": "Autonomous Debugging Workflow Completed",
        "verified": verified,
        "status": status,
        "iterations_used": iteration_count,
        "max_iterations": max_iterations,
        "project_name": state.get("project_name", "Single File"),
        "language": state.get("language", "python").capitalize(),
        "build_system": state.get("build_system", "pytest"),
        "files_analyzed": len(state.get("source_files", [])) + len(state.get("test_files", [])) or 1,
        "suspected_location": state.get("bug_investigation", {}).get("suspected_location"),
        "root_cause": state.get("root_cause", {}).get("root_cause"),
        "bug_category": state.get("root_cause", {}).get("bug_category"),
        "fixed_code": candidate_fix.get("fixed_code"),
        "patches": candidate_fix.get("patches", []),
        "explanation": candidate_fix.get("explanation"),
        "test_status": test_results.get("status"),
        "tests_passed": test_results.get("passed", 0),
        "tests_failed": test_results.get("failed", 0),
        "reason": verification_result.get("reason")
    }

    return {
        "iteration_count": iteration_count,
        "history": updated_history,
        "final_report": final_report
    }


def should_continue(state: Dict[str, Any]) -> str:
    """
    Conditional edge router for LangGraph orchestration workflow.
    Determines whether to finish debugging or retry fix generation.
    """
    verification_result = state.get("verification_result", {})
    verified = verification_result.get("verified", False)
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)

    if verified:
        return "end"
    
    if iteration_count >= max_iterations:
        return "end"

    return "retry_fix"
