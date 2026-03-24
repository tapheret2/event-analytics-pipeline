Fixes #26

This PR addresses two security issues:

- **Unsafe pickle deserialization** in task persistence (RCE risk): migrated persistence to JSON.
- **Command injection** in CSV export: replaced shell-based echo commands with safe Python `csv` writing.

### Changes
- `src/models/task.py`: persist tasks as JSON; safe load with error handling.
- `src/services/task_service.py`: export CSV via `csv.writer` (no shell).
- Add regression tests to prevent reintroducing these vulnerabilities.
