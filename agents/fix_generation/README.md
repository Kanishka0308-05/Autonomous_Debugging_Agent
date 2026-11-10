# Fix Generation Agent

## 1. Purpose
The **Fix Generation Agent** produces candidate Python code fixes addressing the root cause identified by the Root Cause Agent. It avoids overwriting the original user source code directly and stores candidate fixes separately in the state.

## 2. Input
- `source_code` (string): Original buggy source code.
- `root_cause` (dict): Root cause findings.
- `bug_investigation` (dict): Suspicious code location details.
- `verification_result` (optional dict): Feedback from previous failed iteration attempts.

## 3. Processing
- Prompts Gemini LLM to make minimal, surgical edits rather than rewriting the full file.
- Incorporates failure feedback if the previous fix failed testing or verification.
- Uses fallback pattern-matching fix generator if Gemini LLM is unavailable.

## 4. Output
Structured dictionary stored in `candidate_fix`:
```json
{
  "explanation": "Added an explicit check for empty list / zero count before division.",
  "fixed_code": "def calculate_average(numbers):\n    total = sum(numbers)\n    count = len(numbers)\n    if not numbers or count == 0:\n        return 0.0\n    return total / count",
  "changed_section": "+ if not numbers or count == 0:\n+     return 0.0"
}
```

## 5. Shared LangGraph Communication
Reads `state["source_code"]`, `state["root_cause"]`, `state["bug_investigation"]`, `state["verification_result"]` and updates `state["candidate_fix"]`.
