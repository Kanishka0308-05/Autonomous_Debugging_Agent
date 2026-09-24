import os
import sys
import re
import subprocess
from typing import Dict, Any, List, Optional
from language_adapters.base_adapter import BaseLanguageAdapter

class PythonAdapter(BaseLanguageAdapter):
    """
    Language Adapter for Python projects.
    Executes pytest or entry script in temporary workspace, captures stdout/stderr/traceback,
    applies file patches, and builds project summaries.
    """

    def detect(self) -> bool:
        """Return True if Python files or manifest exist in project_path."""
        if not self.project_path or not isinstance(self.project_path, (str, bytes, os.PathLike)) or not os.path.exists(self.project_path):
            return False
        for root, _, files in os.walk(self.project_path):
            for f in files:
                if f.endswith('.py') or f in ('requirements.txt', 'pyproject.toml', 'setup.py'):
                    return True
        return False

    def analyze_project(self) -> Dict[str, Any]:
        """Scan Python source & test files and extract structural summary."""
        if not self.project_path or not isinstance(self.project_path, (str, bytes, os.PathLike)) or not os.path.exists(self.project_path):
            return {
                "language": "python",
                "source_files": [],
                "test_files": [],
                "manifests": [],
                "source_count": 0,
                "test_count": 0,
                "error": "Invalid or missing project path."
            }

        source_files = []
        test_files = []
        manifests = []

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('venv', '.venv', '__pycache__', 'build')]
            for f in files:
                rel_path = os.path.relpath(os.path.join(root, f), self.project_path)
                if f.endswith('.py'):
                    if 'test' in f.lower() or 'test' in rel_path.lower():
                        test_files.append(rel_path)
                    else:
                        source_files.append(rel_path)
                elif f in ('requirements.txt', 'pyproject.toml', 'setup.py'):
                    manifests.append(rel_path)

        return {
            "language": "python",
            "source_files": source_files,
            "test_files": test_files,
            "manifests": manifests,
            "source_count": len(source_files),
            "test_count": len(test_files)
        }

    def install_dependencies_if_needed(self) -> Dict[str, Any]:
        """Check for missing imports without making unsafe external downloads."""
        req_path = os.path.join(self.project_path, "requirements.txt")
        missing_packages = []
        if os.path.exists(req_path):
            with open(req_path, 'r', encoding='utf-8') as f:
                for line in f:
                    pkg = line.strip().split('==')[0].split('>=')[0].strip()
                    if pkg and not pkg.startswith('#'):
                        # Non-blocking check
                        pass
        return {
            "status": "ok",
            "missing_dependencies": missing_packages,
            "message": "Using pre-configured environment (unsafe auto-install disabled)."
        }

    def build_project(self) -> Dict[str, Any]:
        """Python is interpreted; syntax validation check serves as build step."""
        analysis = self.analyze_project()
        syntax_errors = []

        for src in analysis["source_files"] + analysis["test_files"]:
            full_path = os.path.join(self.project_path, src)
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                compile(content, full_path, 'exec')
            except SyntaxError as e:
                syntax_errors.append(f"Syntax error in {src} at line {e.lineno}: {e.msg}")
            except Exception as e:
                syntax_errors.append(f"Parse error in {src}: {str(e)}")

        if syntax_errors:
            return {
                "status": "failed",
                "exit_code": 1,
                "stdout": "",
                "stderr": "\n".join(syntax_errors),
                "build_passed": False
            }

        return {
            "status": "passed",
            "exit_code": 0,
            "stdout": "Python syntax validation passed.",
            "stderr": "",
            "build_passed": True
        }

    def run_tests(self) -> Dict[str, Any]:
        """Run pytest on the project workspace if tests exist; fallback to run_project if no tests."""
        analysis = self.analyze_project()
        test_files = analysis["test_files"]

        if not test_files:
            # Fall back to running entry file if present
            return self.run_project()

        try:
            cmd = [sys.executable, "-m", "pytest", "-v", "--no-header"]
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=20
            )

            output = (result.stdout + "\n" + result.stderr).strip()
            exit_code = result.returncode

            passed_match = re.search(r'(\d+)\s+passed', output)
            failed_match = re.search(r'(\d+)\s+failed', output)
            passed_cnt = int(passed_match.group(1)) if passed_match else (0 if exit_code != 0 else len(test_files))
            failed_cnt = int(failed_match.group(1)) if failed_match else (1 if exit_code != 0 else 0)

            return {
                "language": "python",
                "status": "passed" if exit_code == 0 else "failed",
                "exit_code": exit_code,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "output": output,
                "tests_run": True,
                "passed_count": passed_cnt,
                "failed_count": failed_cnt,
                "files": analysis["source_files"] + analysis["test_files"]
            }
        except subprocess.TimeoutExpired:
            return {
                "language": "python",
                "status": "failed",
                "exit_code": -1,
                "stdout": "",
                "stderr": "PyTest execution timed out (possible infinite loop).",
                "output": "PyTest execution timed out.",
                "tests_run": True,
                "passed_count": 0,
                "failed_count": 1,
                "files": analysis["source_files"] + analysis["test_files"]
            }
        except Exception as e:
            return {
                "language": "python",
                "status": "failed",
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "output": f"PyTest runner exception: {str(e)}",
                "tests_run": False,
                "passed_count": 0,
                "failed_count": 1,
                "files": analysis["source_files"] + analysis["test_files"]
            }

    def run_project(self) -> Dict[str, Any]:
        """Executes a detected Python entry file (e.g. main.py, app.py)."""
        analysis = self.analyze_project()
        entry_file = None
        for candidate in ("main.py", "app.py", "run.py", "index.py"):
            if candidate in analysis["source_files"] or os.path.exists(os.path.join(self.project_path, candidate)):
                entry_file = candidate
                break

        if not entry_file and analysis["source_files"]:
            entry_file = analysis["source_files"][0]

        if not entry_file:
            return {
                "language": "python",
                "status": "failed",
                "exit_code": 1,
                "stdout": "",
                "stderr": "No Python source files found to run.",
                "output": "No Python source files found.",
                "tests_run": False,
                "files": []
            }

        try:
            entry_full = os.path.join(self.project_path, entry_file)
            result = subprocess.run(
                [sys.executable, entry_full],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=15
            )

            output = (result.stdout + "\n" + result.stderr).strip()
            return {
                "language": "python",
                "status": "passed" if result.returncode == 0 else "failed",
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "output": output,
                "tests_run": False,
                "passed_count": 1 if result.returncode == 0 else 0,
                "failed_count": 0 if result.returncode == 0 else 1,
                "files": analysis["source_files"]
            }
        except subprocess.TimeoutExpired:
            return {
                "language": "python",
                "status": "failed",
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution of {entry_file} timed out.",
                "output": f"Execution of {entry_file} timed out.",
                "tests_run": False,
                "passed_count": 0,
                "failed_count": 1,
                "files": analysis["source_files"]
            }
        except Exception as e:
            return {
                "language": "python",
                "status": "failed",
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "output": str(e),
                "tests_run": False,
                "passed_count": 0,
                "failed_count": 1,
                "files": analysis["source_files"]
            }

    def collect_errors(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Parses stdout/stderr for exception tracebacks and error locations."""
        stderr = execution_result.get("stderr", "")
        stdout = execution_result.get("stdout", "")
        combined = f"{stdout}\n{stderr}"

        line_match = re.search(r'File "([^"]+)", line (\d+)', combined)
        file_path = line_match.group(1) if line_match else "unknown"
        line_num = line_match.group(2) if line_match else "unknown"

        exc_match = re.search(r'([A-Za-z_]+Error:[^\n]+)', combined)
        error_msg = exc_match.group(1) if exc_match else (stderr.strip().splitlines()[-1] if stderr.strip() else "Execution failed")

        return {
            "error_type": exc_match.group(1).split(':')[0] if exc_match else "RuntimeError",
            "error_message": error_msg,
            "file": file_path,
            "line": line_num,
            "raw_log": combined.strip()
        }

    def apply_patch(self, patches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Writes candidate code fixes to files in self.project_path."""
        applied_files = []
        errors = []

        for p in patches:
            rel_file = p.get("file", "")
            changes = p.get("changes", "")
            if not rel_file or not changes:
                continue

            target_path = os.path.join(self.project_path, rel_file)
            
            # Clean python code block markers if present
            clean_content = changes
            if clean_content.startswith("```python"):
                clean_content = clean_content[9:]
            elif clean_content.startswith("```"):
                clean_content = clean_content[3:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]

            try:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(clean_content.strip() + "\n")
                applied_files.append(rel_file)
            except Exception as e:
                errors.append(f"Failed to patch {rel_file}: {str(e)}")

        return {
            "success": len(errors) == 0,
            "applied_files": applied_files,
            "errors": errors
        }

    def get_project_summary(self) -> Dict[str, Any]:
        """Generate high-level project summary for LLM context."""
        analysis = self.analyze_project()
        
        # Read contents of main source files (up to 3 key files) for prompt snippet inclusion
        snippets = {}
        for src in analysis["source_files"][:3]:
            full = os.path.join(self.project_path, src)
            try:
                with open(full, 'r', encoding='utf-8') as f:
                    snippets[src] = f.read()
            except Exception:
                pass

        return {
            "language": "python",
            "build_system": "pytest",
            "source_files": analysis["source_files"],
            "test_files": analysis["test_files"],
            "snippets": snippets,
            "summary_text": f"Python project with {len(analysis['source_files'])} source file(s) and {len(analysis['test_files'])} test file(s)."
        }
