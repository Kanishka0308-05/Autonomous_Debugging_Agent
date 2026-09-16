# Bug Investigation Agent

## 1. Purpose
The **Bug Investigation Agent** analyzes the Python source code, error stack trace, and AST analysis to pinpoint the exact location and line of code causing the runtime error.

## 2. Input
- `source_code` (string): Python source code.
- `error_log` (string): Exception stack trace.
- `code_analysis` (dict): AST summary from Code Analysis Agent.

## 3. Processing
- Constructs a prompt sent to Gemini LLM with system instructions enforcing JSON output.
- Analyzes stack trace frames to match code lines.
- If Gemini API key is missing or call fails, invokes `fallback_bug_investigation()` regex stack trace extractor.

## 4. Output
Structured dictionary stored in `bug_investigation`:
```json
{
  "suspected_location": "calculate_average() line 4",
  "suspicious_code": "return total / count",
  "reason": "count can become zero when an empty list is supplied",
  "confidence": "High"
}
```

## 5. Shared LangGraph Communication
Reads `state["source_code"]`, `state["error_log"]`, `state["code_analysis"]` and updates `state["bug_investigation"]`.
