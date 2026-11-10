import ast
import os
from typing import Dict, Any, List
from language_adapters.python.adapter import PythonAdapter
from language_adapters.java.adapter import JavaAdapter

def parse_python_ast(source_code: str) -> Dict[str, Any]:
    """
    Parses Python source code using standard library `ast` module.
    Extracts structural components: functions, classes, imports, and variables.
    """
    result = {
        "functions": [],
        "classes": [],
        "imports": [],
        "variables": [],
        "syntax_valid": True,
        "syntax_error": None,
        "tree_sitter_available": False,
        "summary": ""
    }

    try:
        import tree_sitter
        result["tree_sitter_available"] = True
    except ImportError:
        result["tree_sitter_available"] = False

    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        result["syntax_valid"] = False
        result["syntax_error"] = f"SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}"
        result["summary"] = f"Invalid Python syntax: {e.msg}"
        return result
    except Exception as e:
        result["syntax_valid"] = False
        result["syntax_error"] = str(e)
        result["summary"] = f"Parsing error: {str(e)}"
        return result

    functions = []
    classes = []
    imports = []
    variables = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}")
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            variables.add(node.id)

    result["functions"] = sorted(list(set(functions)))
    result["classes"] = sorted(list(set(classes)))
    result["imports"] = sorted(list(set(imports)))
    result["variables"] = sorted(list(variables))
    
    fn_str = ", ".join(result["functions"]) if result["functions"] else "None"
    cls_str = ", ".join(result["classes"]) if result["classes"] else "None"
    result["summary"] = f"Valid syntax. Found {len(result['functions'])} function(s): [{fn_str}], {len(result['classes'])} class(es): [{cls_str}]."

    return result


def analyze_code_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Code Analysis Agent Node for LangGraph.
    Handles both single-file mode and full multi-file project analysis.
    """
    project_path = state.get("project_path")
    language = state.get("language", "python")

    if project_path and os.path.exists(project_path):
        # Project upload mode
        if language == "java":
            adapter = JavaAdapter(project_path)
        else:
            adapter = PythonAdapter(project_path)

        analysis = adapter.analyze_project()
        summary_info = adapter.get_project_summary()

        analysis_result = {
            "is_project": True,
            "language": language,
            "build_system": summary_info.get("build_system", "unknown"),
            "functions": [],
            "classes": [],
            "imports": [],
            "source_files": analysis.get("source_files", []),
            "test_files": analysis.get("test_files", []),
            "syntax_valid": True,
            "summary": summary_info.get("summary_text", f"Analyzed {language.capitalize()} project."),
            "snippets": summary_info.get("snippets", {})
        }
        return {
            "code_analysis": analysis_result,
            "source_files": analysis.get("source_files", []),
            "test_files": analysis.get("test_files", [])
        }

    # Single-file mode
    source_code = state.get("source_code", "")
    analysis_result = parse_python_ast(source_code)
    analysis_result["is_project"] = False

    return {
        "code_analysis": analysis_result
    }
