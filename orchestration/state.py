from typing import TypedDict, List, Dict, Any, Optional

class DebuggingState(TypedDict):
    """
    Shared state object maintained across all 7 specialized agents in the LangGraph workflow.
    Supports both single-file Python debugging and multi-file Python/Java project uploads.
    """
    source_code: str
    error_log: str
    test_code: Optional[str]
    code_analysis: Optional[Dict[str, Any]]
    bug_investigation: Optional[Dict[str, Any]]
    root_cause: Optional[Dict[str, Any]]
    candidate_fix: Optional[Dict[str, Any]]
    test_results: Optional[Dict[str, Any]]
    verification_result: Optional[Dict[str, Any]]
    iteration_count: int
    max_iterations: int
    history: List[Dict[str, Any]]
    final_report: Optional[Dict[str, Any]]
    is_mock_mode: bool

    # New fields for project upload & multi-language support
    input_mode: Optional[str]           # "single_file" or "project"
    project_path: Optional[str]         # Path to temporary workspace directory
    project_name: Optional[str]         # e.g., "my_project.zip"
    language: Optional[str]             # "python" or "java"
    build_system: Optional[str]         # "pytest", "maven", "gradle", etc.
    project_summary: Optional[Dict[str, Any]]
    source_files: Optional[List[str]]
    test_files: Optional[List[str]]
    execution_result: Optional[Dict[str, Any]]
    compiler_errors: Optional[str]
    runtime_errors: Optional[str]
    test_failures: Optional[str]
    changed_files: Optional[List[str]]
    patches: Optional[List[Dict[str, Any]]]
    classified_error: Optional[Dict[str, Any]]
