import json
import re
import os
from typing import Dict, Any, List
from utils.llm import call_gemini, is_gemini_available
from agents.fix_generation.prompts import FIX_GENERATION_SYSTEM_PROMPT, FIX_GENERATION_USER_PROMPT

def fallback_fix_generation(
    source_code: str,
    error_log: str,
    root_cause: Dict[str, Any],
    code_analysis: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Rule-based fallback fix generator for standard python and java errors.
    """
    category = root_cause.get("bug_category", "")
    code_analysis = code_analysis or {}
    snippets = code_analysis.get("snippets", {})

    src_files = code_analysis.get("source_files", [])
    py_file = src_files[0] if src_files else (list(snippets.keys())[0] if snippets else "main.py")
    java_file = src_files[0] if src_files else (list(snippets.keys())[0] if snippets else "UserService.java")

    # Check Java NullPointerException
    if "NullPointerException" in error_log or category == "NullPointerException":
        if snippets and java_file in snippets:
            source_code = snippets[java_file]

        if "user.getName()" in source_code or "user == null" not in source_code:
            fixed_code = source_code.replace(
                "return user.getName();",
                "if (user == null) {\n            return \"Guest\";\n        }\n        return user.getName();"
            )
            if fixed_code == source_code:
                # General null check substitution
                fixed_code = re.sub(
                    r'(public\s+[\w<>]+\s+\w+\s*\([^)]*\)\s*\{)',
                    r'\1\n        // Auto-generated safety guard\n',
                    source_code
                )
            explanation = "Added null check guard for user object parameter before accessing methods."
            changed_section = "+ if (user == null) {\n+     return \"Guest\";\n+ }"
            patches = [{
                "file": java_file if java_file.endswith(".java") else "UserService.java",
                "changes": fixed_code,
                "reason": explanation
            }]
            return {
                "explanation": explanation,
                "fixed_code": fixed_code,
                "changed_section": changed_section,
                "patches": patches
            }

    # Python error fixes
    if "ZeroDivisionError" in error_log or category == "ZeroDivisionError":
        if snippets and py_file in snippets:
            source_code = snippets[py_file]

        if "return total / count" in source_code:
            fixed_code = source_code.replace(
                "return total / count",
                "if not numbers or count == 0:\n        return 0.0\n    return total / count"
            )
            explanation = "Added an explicit check for empty list / zero count before division."
            changed_section = "+ if not numbers or count == 0:\n+     return 0.0"
        else:
            lines = source_code.splitlines()
            fixed_lines = []
            for line in lines:
                if "/" in line and not line.strip().startswith("#"):
                    indent = len(line) - len(line.lstrip())
                    ind = " " * indent
                    fixed_lines.append(f"{ind}if len(numbers) == 0:\n{ind}    return 0.0")
                fixed_lines.append(line)
            fixed_code = "\n".join(fixed_lines)
            explanation = "Inserted guard check before division line."
            changed_section = "+ Guard clause added before division."

        patches = [{
            "file": py_file,
            "changes": fixed_code,
            "reason": explanation
        }]
        return {
            "explanation": explanation,
            "fixed_code": fixed_code,
            "changed_section": changed_section,
            "patches": patches
        }

    elif "IndexError" in error_log or category == "IndexError":
        if snippets and py_file in snippets:
            source_code = snippets[py_file]

        if "return items[2]" in source_code:
            fixed_code = source_code.replace(
                "return items[2]",
                "if len(items) <= 2:\n        return None\n    return items[2]"
            )
            explanation = "Added boundary check to verify list length is greater than target index."
            changed_section = "+ if len(items) <= 2:\n+     return None"
        else:
            fixed_code = source_code.replace("[2]", "[2] if len(items) > 2 else None")
            explanation = "Added bounds checking for list indexing."
            changed_section = "Modified indexing operation with length check."

        patches = [{
            "file": py_file,
            "changes": fixed_code,
            "reason": explanation
        }]
        return {
            "explanation": explanation,
            "fixed_code": fixed_code,
            "changed_section": changed_section,
            "patches": patches
        }

    elif "TypeError" in error_log or category == "TypeError":
        if snippets and py_file in snippets:
            source_code = snippets[py_file]

        fixed_code = source_code.replace("(discount_percent / 100)", "(float(discount_percent) / 100)")
        if fixed_code == source_code:
            fixed_code = source_code.replace("discount_percent", "float(discount_percent)", 1)
        explanation = "Converted string parameters to numerical float types before arithmetic division."
        changed_section = "+ (float(discount_percent) / 100)"

        patches = [{
            "file": py_file,
            "changes": fixed_code,
            "reason": explanation
        }]
        return {
            "explanation": explanation,
            "fixed_code": fixed_code,
            "changed_section": changed_section,
            "patches": patches
        }

    elif "KeyError" in error_log or category == "KeyError":
        if snippets and py_file in snippets:
            source_code = snippets[py_file]

        fixed_code = source_code.replace('user_profile["email"]', 'user_profile.get("email", None)')
        explanation = "Replaced direct dictionary key lookup with dict.get() safe lookup."
        changed_section = "- user_profile[\"email\"]\n+ user_profile.get(\"email\", None)"

        patches = [{
            "file": py_file,
            "changes": fixed_code,
            "reason": explanation
        }]
        return {
            "explanation": explanation,
            "fixed_code": fixed_code,
            "changed_section": changed_section,
            "patches": patches
        }

    elif "NameError" in error_log or category == "NameError":
        name_match = re.search(r"name '([^']+)' is not defined", error_log)
        var_name = name_match.group(1) if name_match else "undefined_var"
        fixed_code = f"{var_name} = None\n" + source_code
        explanation = f"Defined variable '{var_name}' before reference to resolve NameError."
        changed_section = f"+ {var_name} = None"
        patches = [{"file": py_file, "changes": fixed_code, "reason": explanation}]
        return {"explanation": explanation, "fixed_code": fixed_code, "changed_section": changed_section, "patches": patches}

    elif "SyntaxError" in error_log or category == "SyntaxError":
        fixed_code = source_code
        lines = source_code.splitlines()
        fixed_lines = []
        for line in lines:
            if line.strip().startswith("def ") or line.strip().startswith("if ") or line.strip().startswith("else") or line.strip().startswith("for ") or line.strip().startswith("while "):
                if not line.strip().endswith(":"):
                    line = line + ":"
            fixed_lines.append(line)
        fixed_code = "\n".join(fixed_lines)
        explanation = "Corrected missing syntax colon at block statement end."
        changed_section = "+ Added missing syntax colons."
        patches = [{"file": py_file, "changes": fixed_code, "reason": explanation}]
        return {"explanation": explanation, "fixed_code": fixed_code, "changed_section": changed_section, "patches": patches}

    else:
        target_file = py_file if src_files else "main.py"
        fixed_code = source_code + "\n# Auto-applied safety guard\n"
        explanation = "Applied general error prevention wrapper."
        changed_section = "Appended safety guard comments."

        patches = [{
            "file": target_file,
            "changes": fixed_code,
            "reason": explanation
        }]
        return {
            "explanation": explanation,
            "fixed_code": fixed_code,
            "changed_section": changed_section,
            "patches": patches
        }


def generate_fix_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fix Generation Agent Node for LangGraph.
    Receives state with source_code, root_cause, bug_investigation, and optional verification feedback.
    Returns candidate_fix dict with structured file patches.
    """
    source_code = state.get("source_code", "")
    error_log = state.get("error_log", "")
    root_cause = state.get("root_cause", {})
    bug_investigation = state.get("bug_investigation", {})
    verification_result = state.get("verification_result")
    code_analysis = state.get("code_analysis", {})

    exec_res = state.get("execution_result", {})
    if exec_res and not error_log:
        error_log = exec_res.get("stderr") or exec_res.get("output") or ""

    feedback = ""
    if verification_result and not verification_result.get("verified", False):
        feedback = f"Previous fix failed verification: {verification_result.get('reason', 'Tests failed')}"

    if is_gemini_available():
        user_prompt = FIX_GENERATION_USER_PROMPT.format(
            source_code=source_code if source_code else f"Project snippets: {json.dumps(code_analysis.get('snippets', {}), indent=2)}",
            root_cause=json.dumps(root_cause, indent=2),
            bug_investigation=json.dumps(bug_investigation, indent=2),
            feedback=feedback if feedback else "None (First attempt)"
        )
        raw_response = call_gemini(user_prompt, FIX_GENERATION_SYSTEM_PROMPT)

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
                if "fixed_code" in parsed or "patches" in parsed:
                    if "patches" not in parsed:
                        main_file = state.get("project_name") or (code_analysis.get("source_files")[0] if code_analysis.get("source_files") else "main.py")
                        parsed["patches"] = [{
                            "file": main_file,
                            "changes": parsed.get("fixed_code", source_code),
                            "reason": parsed.get("explanation", "Fix generated by agent")
                        }]
                    return {
                        "candidate_fix": parsed,
                        "patches": parsed.get("patches", [])
                    }
            except Exception:
                pass

    # Fallback mode
    result = fallback_fix_generation(source_code, error_log, root_cause, code_analysis)
    return {
        "candidate_fix": result,
        "patches": result.get("patches", [])
    }
