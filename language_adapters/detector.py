import os
from typing import Dict, Any, List

def detect_project(project_path: str) -> Dict[str, Any]:
    """
    Inspects a project directory and determines:
    - Primary programming language (Python, Java, or multiple/unsupported)
    - Build system (pytest, maven, gradle)
    - Source and test directories
    - Entry points and dependency manifests
    """
    if not os.path.exists(project_path) or not os.path.isdir(project_path):
        return {
            "language": "unknown",
            "detected_languages": [],
            "build_system": "unknown",
            "is_supported": False,
            "message": "Invalid project directory path."
        }

    py_files = []
    java_files = []
    cpp_files = []
    other_code_files = []

    has_requirements = os.path.exists(os.path.join(project_path, "requirements.txt"))
    has_pyproject = os.path.exists(os.path.join(project_path, "pyproject.toml"))
    has_setup_py = os.path.exists(os.path.join(project_path, "setup.py"))

    has_pom = os.path.exists(os.path.join(project_path, "pom.xml"))
    has_gradle = (
        os.path.exists(os.path.join(project_path, "build.gradle")) or
        os.path.exists(os.path.join(project_path, "build.gradle.kts"))
    )

    all_files = []
    test_files = []

    for root, dirs, files in os.walk(project_path):
        # Exclude hidden, venv, and target dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('venv', '.venv', 'target', 'build', '__pycache__', 'node_modules')]
        for f in files:
            rel_path = os.path.relpath(os.path.join(root, f), project_path)
            all_files.append(rel_path)
            
            ext = os.path.splitext(f)[1].lower()
            if ext == '.py':
                py_files.append(rel_path)
                if 'test' in f.lower() or 'test' in rel_path.lower():
                    test_files.append(rel_path)
            elif ext == '.java':
                java_files.append(rel_path)
                if 'test' in f.lower() or 'test' in rel_path.lower():
                    test_files.append(rel_path)
            elif ext in ('.cpp', '.c', '.h', '.hpp', '.cs'):
                cpp_files.append(rel_path)
            elif ext in ('.js', '.ts', '.go', '.rs'):
                other_code_files.append(rel_path)

    detected_languages = []
    if py_files or has_requirements or has_pyproject or has_setup_py:
        detected_languages.append("python")
    if java_files or has_pom or has_gradle:
        detected_languages.append("java")
    if cpp_files:
        detected_languages.append("cpp")

    if not detected_languages:
        return {
            "language": "unknown",
            "detected_languages": [],
            "build_system": "unknown",
            "is_supported": False,
            "message": "Unsupported or empty project. Currently supported languages: Python and Java.",
            "files_count": len(all_files),
            "test_files_count": len(test_files)
        }

    if len(detected_languages) > 1 and "cpp" not in detected_languages:
        # Multi-language project (e.g., both Python and Java detected)
        return {
            "language": "multiple",
            "detected_languages": detected_languages,
            "build_system": "multiple",
            "is_supported": True,
            "message": "Multiple languages detected (Python and Java). Please select target language.",
            "py_files": py_files,
            "java_files": java_files,
            "files_count": len(all_files),
            "test_files_count": len(test_files)
        }

    if "cpp" in detected_languages and len(detected_languages) == 1:
        return {
            "language": "cpp",
            "detected_languages": ["cpp"],
            "build_system": "unknown",
            "is_supported": False,
            "message": "Currently supported languages: Python and Java.",
            "files_count": len(all_files),
            "test_files_count": len(test_files)
        }

    primary_lang = detected_languages[0]

    # Determine build system & directories
    build_system = "unknown"
    source_dir = ""
    test_dir = ""
    entry_points = []
    dependency_files = []

    if primary_lang == "python":
        build_system = "pytest"
        if has_requirements:
            dependency_files.append("requirements.txt")
        if has_pyproject:
            dependency_files.append("pyproject.toml")
        if has_setup_py:
            dependency_files.append("setup.py")

        # Detect potential entry point
        for main_candidate in ("main.py", "app.py", "run.py", "index.py"):
            if any(f.endswith(main_candidate) for f in py_files):
                entry_points.append(main_candidate)

        source_dir = os.path.dirname(py_files[0]) if py_files else "."
        test_dir = os.path.dirname(test_files[0]) if test_files else "."

    elif primary_lang == "java":
        if has_pom:
            build_system = "maven"
            dependency_files.append("pom.xml")
        elif has_gradle:
            build_system = "gradle"
            if os.path.exists(os.path.join(project_path, "build.gradle")):
                dependency_files.append("build.gradle")
            if os.path.exists(os.path.join(project_path, "build.gradle.kts")):
                dependency_files.append("build.gradle.kts")
        else:
            build_system = "java-direct"

        source_dir = "src/main/java" if os.path.exists(os.path.join(project_path, "src", "main", "java")) else "."
        test_dir = "src/test/java" if os.path.exists(os.path.join(project_path, "src", "test", "java")) else "."

    return {
        "language": primary_lang,
        "detected_languages": detected_languages,
        "build_system": build_system,
        "is_supported": True,
        "source_directory": source_dir,
        "test_directory": test_dir,
        "entry_points": entry_points,
        "dependency_files": dependency_files,
        "source_files": py_files if primary_lang == "python" else java_files,
        "test_files": test_files,
        "files_count": len(all_files),
        "test_files_count": len(test_files),
        "message": f"Successfully detected {primary_lang.capitalize()} project ({build_system})."
    }
