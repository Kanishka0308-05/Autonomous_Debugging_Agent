# Testing Agent

## 1. Purpose
The **Testing Agent** receives candidate fixed code from the Fix Generation Agent, writes it into an isolated temporary workspace alongside test assertions, executes `pytest` via Python `subprocess`, and captures test metrics.

## 2. Input
- `candidate_fix` (dict): Candidate fixed Python code.
- `test_code` (optional string): Custom unit test assertions (if provided by user/demo).

## 3. Processing
- Creates a local temporary directory using `tempfile.TemporaryDirectory()`.
- Writes `solution.py` and `test_solution.py`.
- Invokes `python -m pytest test_solution.py -v` via `subprocess.run()`.
- Captures test output, stdout, stderr, execution status, and pass/fail counts.
- Implements execution timeouts to safeguard against infinite loop regressions.

## 4. Output
Structured dictionary stored in `test_results`:
```json
{
  "tests_run": 2,
  "passed": 2,
  "failed": 0,
  "status": "PASS",
  "output": "2 passed in 0.03s",
  "exit_code": 0
}
```

## 5. Shared LangGraph Communication
Reads `state["candidate_fix"]`, `state["test_code"]` and updates `state["test_results"]`.
