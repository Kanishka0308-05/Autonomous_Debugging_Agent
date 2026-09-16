# Code Analysis Agent

## 1. Purpose
The **Code Analysis Agent** performs static code analysis on user-submitted Python source code. It validates structural syntax and extracts essential components such as functions, classes, imported modules, and variable assignments.

## 2. Input
- `source_code` (string): The Python source code submitted for debugging.

## 3. Processing
- Parses the Python string using standard library `ast.parse()`.
- Walks the Abstract Syntax Tree (AST) to discover `ast.FunctionDef`, `ast.ClassDef`, `ast.Import`, and `ast.Name` nodes.
- Checks if optional `tree-sitter` parser library is present without raising errors if absent.
- Traps `SyntaxError` exceptions and flags invalid syntax gracefully.

## 4. Output
Structured dictionary assigned to `code_analysis` in the shared LangGraph state:
```json
{
  "functions": ["calculate_average"],
  "classes": [],
  "imports": ["math"],
  "variables": ["total", "count"],
  "syntax_valid": true,
  "syntax_error": null,
  "tree_sitter_available": false,
  "summary": "Valid syntax. Found 1 function(s): [calculate_average], 0 class(es): [None]."
}
```

## 5. Shared LangGraph Communication
Reads `state["source_code"]` and returns `{"code_analysis": result}` to update the shared `DebuggingState`.
