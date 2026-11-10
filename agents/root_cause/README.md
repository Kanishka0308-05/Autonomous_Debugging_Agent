# Root Cause Agent

## 1. Purpose
The **Root Cause Agent** explains *why* the identified bug occurs, categorizes the bug type, and outlines the structural logic deficiency to be corrected.

## 2. Input
- `source_code` (string): Original source code.
- `error_log` (string): Stack trace exception log.
- `bug_investigation` (dict): Output from Bug Investigation Agent.

## 3. Processing
- Queries Gemini LLM with root cause analysis instructions.
- Distinguishes between root causes (e.g. unhandled empty list) vs immediate symptom (division by zero).
- Provides fallback analysis if LLM API is unavailable.

## 4. Output
Structured dictionary stored in `root_cause`:
```json
{
  "root_cause": "The function divides by count without checking whether the input list is empty.",
  "bug_category": "ZeroDivisionError",
  "explanation": "When the list is empty, count becomes 0 and total / count raises ZeroDivisionError.",
  "recommended_fix_strategy": "Add an empty guard check: return 0.0 if not numbers else total / count"
}
```

## 5. Shared LangGraph Communication
Reads `state["bug_investigation"]`, `state["error_log"]` and updates `state["root_cause"]`.
