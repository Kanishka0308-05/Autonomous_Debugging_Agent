# Verification Agent

## 1. Purpose
The **Verification Agent** performs final validation on the candidate fix. It inspects test execution output from the Testing Agent, cross-checks against the original error condition, and assigns an authoritative status: `VERIFIED` or `FAILED`.

## 2. Input
- `error_log` (string): Original error log.
- `root_cause` (dict): Root cause findings.
- `candidate_fix` (dict): Candidate code fix.
- `test_results` (dict): Execution results from Testing Agent.

## 3. Processing
- Evaluates test suite pass/fail metrics.
- Uses Gemini LLM to generate a summary justification for the verification status.
- Returns `verified: true` if all tests pass, or `verified: false` if tests fail.

## 4. Output
Structured dictionary stored in `verification_result`:
```json
{
  "verified": true,
  "status": "VERIFIED",
  "reason": "All generated PyTest assertions passed and the original error condition was successfully resolved."
}
```

## 5. Shared LangGraph Communication
Reads `state["test_results"]`, `state["candidate_fix"]` and updates `state["verification_result"]`.
If `verified` is false, Supervisor Agent will route control back to Fix Generation Agent for up to max retry iterations.
