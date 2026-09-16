# Supervisor Agent

## 1. Purpose
The **Supervisor Agent** coordinates the entire autonomous debugging pipeline. It manages shared state, monitors iteration counters, enforces safety boundaries (preventing infinite retry loops), and determines whether to proceed to final report completion or retry fix generation.

## 2. Input
- Shared `DebuggingState` containing all intermediate agent results and `iteration_count`.

## 3. Processing
- Increments `iteration_count` on each pass.
- Appends current snapshot to `history`.
- Evaluates `verification_result`:
  - If `verified == true` -> Routes to `END`.
  - If `verified == false` and `iteration_count < max_iterations` -> Routes back to `fix_generation`.
  - If `iteration_count >= max_iterations` -> Terminates gracefully and compiles final report.

## 4. Output
Updated state fields:
```json
{
  "iteration_count": 1,
  "history": [ ... ],
  "final_report": {
    "summary": "Autonomous Debugging Workflow Completed",
    "verified": true,
    "status": "VERIFIED",
    "iterations_used": 1,
    "max_iterations": 3,
    "suspected_location": "calculate_average() line 4",
    "root_cause": "Division by count without checking if empty",
    "fixed_code": "...",
    "test_status": "PASS"
  }
}
```

## 5. Shared LangGraph Communication
Controls conditional edge routing `should_continue()` in `orchestration/graph.py`.
