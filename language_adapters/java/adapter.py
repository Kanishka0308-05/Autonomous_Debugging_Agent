import os
import sys
import re
import shutil
import subprocess
from typing import Dict, Any, List, Optional
from language_adapters.base_adapter import BaseLanguageAdapter

class JavaAdapter(BaseLanguageAdapter):
    """
    Language Adapter for Java projects.
    Supports Maven, Gradle, and standalone javac execution.
    Prefers wrappers (mvnw.cmd / gradlew.bat on Windows) and captures compilation / test failures.
    """

    def detect(self) -> bool:
        """Return True if Java files or pom.xml / build.gradle exist in project_path."""
        if not os.path.exists(self.project_path):
            return False
        if os.path.exists(os.path.join(self.project_path, "pom.xml")):
            return True
        if os.path.exists(os.path.join(self.project_path, "build.gradle")) or os.path.exists(os.path.join(self.project_path, "build.gradle.kts")):
            return True
        for root, _, files in os.walk(self.project_path):
            for f in files:
                if f.endswith('.java'):
                    return True
        return False

    def analyze_project(self) -> Dict[str, Any]:
        """Scan Java source and test directories and detect build configuration."""
        source_files = []
        test_files = []

        is_maven = os.path.exists(os.path.join(self.project_path, "pom.xml"))
        is_gradle = (
            os.path.exists(os.path.join(self.project_path, "build.gradle")) or
            os.path.exists(os.path.join(self.project_path, "build.gradle.kts"))
        )

        build_system = "maven" if is_maven else ("gradle" if is_gradle else "java-direct")

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('target', 'build', '.gradle', 'bin')]
            for f in files:
                if f.endswith('.java'):
                    rel_path = os.path.relpath(os.path.join(root, f), self.project_path)
                    if 'test' in rel_path.lower() or f.endswith('Test.java') or f.endswith('Tests.java'):
                        test_files.append(rel_path)
                    else:
                        source_files.append(rel_path)

        return {
            "language": "java",
            "build_system": build_system,
            "source_files": source_files,
            "test_files": test_files,
            "source_count": len(source_files),
            "test_count": len(test_files)
        }

    def install_dependencies_if_needed(self) -> Dict[str, Any]:
        """Report missing tools/dependencies safely."""
        build_sys = self.analyze_project()["build_system"]
        missing = []

        if build_sys == "maven" and not self._get_maven_command():
            missing.append("Maven (mvn / mvnw)")
        elif build_sys == "gradle" and not self._get_gradle_command():
            missing.append("Gradle (gradle / gradlew)")
        elif build_sys == "java-direct" and not shutil.which("javac"):
            missing.append("JDK (javac / java)")

        return {
            "status": "ok" if not missing else "warning",
            "missing_dependencies": missing,
            "message": "Environment tools checked." if not missing else f"Missing environment tools: {', '.join(missing)}"
        }

    def _get_maven_command(self) -> Optional[List[str]]:
        """Resolve Maven command prioritizing local wrappers."""
        is_win = sys.platform.startswith("win")
        wrapper_win = os.path.join(self.project_path, "mvnw.cmd")
        wrapper_nix = os.path.join(self.project_path, "mvnw")

        if is_win and os.path.exists(wrapper_win):
            return [wrapper_win]
        elif not is_win and os.path.exists(wrapper_nix):
            return [wrapper_nix]
        elif shutil.which("mvn"):
            return ["mvn"]
        elif shutil.which("mvn.cmd"):
            return ["mvn.cmd"]
        return None

    def _get_gradle_command(self) -> Optional[List[str]]:
        """Resolve Gradle command prioritizing local wrappers."""
        is_win = sys.platform.startswith("win")
        wrapper_win = os.path.join(self.project_path, "gradlew.bat")
        wrapper_nix = os.path.join(self.project_path, "gradlew")

        if is_win and os.path.exists(wrapper_win):
            return [wrapper_win]
        elif not is_win and os.path.exists(wrapper_nix):
            return [wrapper_nix]
        elif shutil.which("gradle"):
            return ["gradle"]
        elif shutil.which("gradle.bat"):
            return ["gradle.bat"]
        return None

    def build_project(self) -> Dict[str, Any]:
        """Builds or compiles Java project."""
        analysis = self.analyze_project()
        build_sys = analysis["build_system"]

        if build_sys == "maven":
            cmd = self._get_maven_command()
            if not cmd:
                return {
                    "status": "failed",
                    "exit_code": 127,
                    "stdout": "",
                    "stderr": "Environment Error: Maven (mvn) or wrapper (mvnw) is not installed or available on PATH.",
                    "build_passed": False
                }
            full_cmd = cmd + ["test-compile", "-B"]
        elif build_sys == "gradle":
            cmd = self._get_gradle_command()
            if not cmd:
                return {
                    "status": "failed",
                    "exit_code": 127,
                    "stdout": "",
                    "stderr": "Environment Error: Gradle (gradle) or wrapper (gradlew) is not installed or available on PATH.",
                    "build_passed": False
                }
            full_cmd = cmd + ["testClasses"]
        else:
            # Standalone javac compilation
            javac_bin = shutil.which("javac")
            if not javac_bin:
                return {
                    "status": "failed",
                    "exit_code": 127,
                    "stdout": "",
                    "stderr": "Environment Error: Java compiler (javac) is not installed or available on PATH.",
                    "build_passed": False
                }
            all_java = [os.path.join(self.project_path, f) for f in analysis["source_files"] + analysis["test_files"]]
            if not all_java:
                return {"status": "passed", "exit_code": 0, "stdout": "No java files to compile.", "stderr": "", "build_passed": True}
            
            bin_dir = os.path.join(self.project_path, "bin")
            os.makedirs(bin_dir, exist_ok=True)
            full_cmd = [javac_bin, "-d", bin_dir] + all_java

        try:
            res = subprocess.run(
                full_cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=45
            )
            output = (res.stdout + "\n" + res.stderr).strip()
            return {
                "status": "passed" if res.returncode == 0 else "failed",
                "exit_code": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "output": output,
                "build_passed": res.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "failed",
                "exit_code": -1,
                "stdout": "",
                "stderr": "Java build command timed out.",
                "output": "Java build command timed out.",
                "build_passed": False
            }
        except Exception as e:
            return {
                "status": "failed",
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "output": str(e),
                "build_passed": False
            }

    def run_tests(self) -> Dict[str, Any]:
        """Executes Java unit tests via Maven, Gradle, or fallback runner."""
        analysis = self.analyze_project()
        build_sys = analysis["build_system"]

        if build_sys == "maven":
            cmd = self._get_maven_command()
            if not cmd:
                return self._environment_error_result("Maven (mvn) or wrapper (mvnw.cmd) is not installed on PATH.")
            full_cmd = cmd + ["test", "-B"]
        elif build_sys == "gradle":
            cmd = self._get_gradle_command()
            if not cmd:
                return self._environment_error_result("Gradle (gradle) or wrapper (gradlew.bat) is not installed on PATH.")
            full_cmd = cmd + ["test"]
        else:
            return self.run_project()

        try:
            res = subprocess.run(
                full_cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=60
            )

            output = (res.stdout + "\n" + res.stderr).strip()
            exit_code = res.returncode

            # Parse Maven test counts
            passed_cnt = 0
            failed_cnt = 0
            tests_run_match = re.search(r'Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)', output)
            if tests_run_match:
                total = int(tests_run_match.group(1))
                failures = int(tests_run_match.group(2))
                errors = int(tests_run_match.group(3))
                failed_cnt = failures + errors
                passed_cnt = total - failed_cnt
            else:
                passed_cnt = 1 if exit_code == 0 else 0
                failed_cnt = 0 if exit_code == 0 else 1

            return {
                "language": "java",
                "build_system": build_sys,
                "status": "passed" if exit_code == 0 else "failed",
                "exit_code": exit_code,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "output": output,
                "tests_run": True,
                "passed_count": passed_cnt,
                "failed_count": failed_cnt,
                "files": analysis["source_files"] + analysis["test_files"]
            }

        except subprocess.TimeoutExpired:
            return {
                "language": "java",
                "build_system": build_sys,
                "status": "failed",
                "exit_code": -1,
                "stdout": "",
                "stderr": "Java test execution timed out.",
                "output": "Java test execution timed out.",
                "tests_run": True,
                "passed_count": 0,
                "failed_count": 1,
                "files": analysis["source_files"] + analysis["test_files"]
            }
        except Exception as e:
            return self._environment_error_result(str(e))

    def run_project(self) -> Dict[str, Any]:
        """Runs direct java entry point class or standalone test if Maven/Gradle unavailable."""
        analysis = self.analyze_project()
        javac_bin = shutil.which("javac")
        java_bin = shutil.which("java")

        if not javac_bin or not java_bin:
            return self._environment_error_result("Java SDK (javac/java) is not installed on system PATH.")

        # Build first
        b_res = self.build_project()
        if not b_res.get("build_passed"):
            return {
                "language": "java",
                "build_system": "java-direct",
                "status": "failed",
                "exit_code": b_res.get("exit_code", 1),
                "stdout": b_res.get("stdout", ""),
                "stderr": b_res.get("stderr", "Compilation failed."),
                "output": b_res.get("output", "Compilation failed."),
                "tests_run": False,
                "passed_count": 0,
                "failed_count": 1,
                "files": analysis["source_files"]
            }

        # Find main class
        main_class = None
        for src in analysis["source_files"]:
            full = os.path.join(self.project_path, src)
            try:
                with open(full, 'r', encoding='utf-8') as f:
                    txt = f.read()
                    if "public static void main" in txt:
                        # Extract class name
                        m = re.search(r'public\s+class\s+([A-Za-z0-9_]+)', txt)
                        if m:
                            main_class = m.group(1)
                            break
            except Exception:
                pass

        if not main_class:
            return {
                "language": "java",
                "build_system": "java-direct",
                "status": "passed",
                "exit_code": 0,
                "stdout": "Java code compiled cleanly. No main method found to execute.",
                "stderr": "",
                "output": "Java compilation successful.",
                "tests_run": False,
                "passed_count": 1,
                "failed_count": 0,
                "files": analysis["source_files"]
            }

        bin_dir = os.path.join(self.project_path, "bin")
        try:
            res = subprocess.run(
                [java_bin, "-cp", bin_dir, main_class],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=15
            )
            output = (res.stdout + "\n" + res.stderr).strip()
            return {
                "language": "java",
                "build_system": "java-direct",
                "status": "passed" if res.returncode == 0 else "failed",
                "exit_code": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "output": output,
                "tests_run": False,
                "passed_count": 1 if res.returncode == 0 else 0,
                "failed_count": 0 if res.returncode == 0 else 1,
                "files": analysis["source_files"]
            }
        except Exception as e:
            return self._environment_error_result(str(e))

    def _environment_error_result(self, error_msg: str) -> Dict[str, Any]:
        """Return clear environment error without crashing application."""
        analysis = self.analyze_project()
        return {
            "language": "java",
            "build_system": analysis.get("build_system", "java"),
            "status": "failed",
            "exit_code": 127,
            "stdout": "",
            "stderr": f"Environment Error: {error_msg}",
            "output": f"Environment Error: {error_msg}\nPlease install Java JDK / Maven / Gradle or run with project wrappers.",
            "tests_run": False,
            "passed_count": 0,
            "failed_count": 1,
            "files": analysis.get("source_files", [])
        }

    def collect_errors(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Parses output/stderr for Java compilation or Exception tracebacks."""
        stderr = execution_result.get("stderr", "")
        output = execution_result.get("output", "")
        combined = f"{output}\n{stderr}"

        # Check NullPointerException or runtime exceptions
        exc_match = re.search(r'([a-zA-Z0-9\.]+(?:Exception|Error)):?\s*([^\n]*)', combined)
        error_type = exc_match.group(1).split('.')[-1] if exc_match else "JavaError"
        error_msg = exc_match.group(0) if exc_match else (stderr.strip().splitlines()[-1] if stderr.strip() else "Java Execution Failure")

        # Find file & line number in Java stack trace
        loc_match = re.search(r'at\s+[\w\.]+\(([A-Za-z0-9_]+\.java):(\d+)\)', combined)
        file_name = loc_match.group(1) if loc_match else "unknown"
        line_num = loc_match.group(2) if loc_match else "unknown"

        return {
            "error_type": error_type,
            "error_message": error_msg,
            "file": file_name,
            "line": line_num,
            "raw_log": combined.strip()
        }

    def apply_patch(self, patches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Writes candidate Java fixes back to file paths in project_path."""
        applied_files = []
        errors = []

        for p in patches:
            rel_file = p.get("file", "")
            changes = p.get("changes", "")
            if not rel_file or not changes:
                continue

            target_path = os.path.join(self.project_path, rel_file)

            clean_content = changes
            if clean_content.startswith("```java"):
                clean_content = clean_content[7:]
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
        """Generate high-level Java project summary for LLM context."""
        analysis = self.analyze_project()
        snippets = {}

        for src in analysis["source_files"][:4]:
            full = os.path.join(self.project_path, src)
            try:
                with open(full, 'r', encoding='utf-8') as f:
                    snippets[src] = f.read()
            except Exception:
                pass

        return {
            "language": "java",
            "build_system": analysis["build_system"],
            "source_files": analysis["source_files"],
            "test_files": analysis["test_files"],
            "snippets": snippets,
            "summary_text": f"Java ({analysis['build_system']}) project with {len(analysis['source_files'])} source file(s) and {len(analysis['test_files'])} test file(s)."
        }
