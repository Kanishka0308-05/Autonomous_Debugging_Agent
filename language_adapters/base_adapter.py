from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseLanguageAdapter(ABC):
    """
    Abstract Base Class defining the interface for language execution adapters.
    Each adapter manages project inspection, build execution, test execution,
    patching, and error extraction for a specific programming language/ecosystem.
    """

    def __init__(self, project_path: str):
        self.project_path = project_path

    @abstractmethod
    def detect(self) -> bool:
        """Determines if the project at project_path matches this language adapter."""
        pass

    @abstractmethod
    def analyze_project(self) -> Dict[str, Any]:
        """Scans project files, source directories, test files, and configuration files."""
        pass

    @abstractmethod
    def install_dependencies_if_needed(self) -> Dict[str, Any]:
        """Reports missing dependencies or safe status (no auto-untrusted-installs)."""
        pass

    @abstractmethod
    def build_project(self) -> Dict[str, Any]:
        """Builds or compiles the project."""
        pass

    @abstractmethod
    def run_tests(self) -> Dict[str, Any]:
        """Executes automated tests in the project."""
        pass

    @abstractmethod
    def run_project(self) -> Dict[str, Any]:
        """Runs the main project entry file if tests are unavailable."""
        pass

    @abstractmethod
    def collect_errors(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts compilation errors, runtime errors, and tracebacks from execution logs."""
        pass

    @abstractmethod
    def apply_patch(self, patches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Applies a list of file patches to the temporary workspace.
        Each patch dict contains:
        {
            "file": "relative/path/to/file.ext",
            "changes": "full file content or modified snippet",
            "reason": "explanation"
        }
        """
        pass

    @abstractmethod
    def get_project_summary(self) -> Dict[str, Any]:
        """Returns a high-level summary of the project for agent consumption."""
        pass
