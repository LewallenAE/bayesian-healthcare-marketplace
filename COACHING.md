# Coaching Protocol — How Sessions Work

## Format: SAY / SEE / DO

Every step follows this structure:

### SAY — Why are we doing this?
- Explains the **reason** this code exists in the system
- Connects it to the larger architecture (what depends on it, what it feeds)
- Calls out production concerns (why Decimal not float, why frozen not mutable, etc.)

### SEE — What does the result look like?
- Target file/folder structure after this step
- No surprises — you know what you're building before you write a line

### DO — What do you write?
- Imports you'll need (with explanation of what each does)
- The structure of the code (class, function, config)
- Field-by-field or line-by-line guidance on **what** to write and **why**
- NOT a code dump — enough detail to write it yourself, not copy-paste

## After You Write

Post back one of:
- Your code (for review before running)
- `pytest -q` output (to confirm it works)
- Error logs (to debug together)

## Review Criteria

Code gets reviewed for:
1. **Correctness** — does it do what it should?
2. **Edge cases** — what inputs break it?
3. **Missing tests** — what behavior isn't covered?
4. **Import hygiene** — correct paths, no `src.` prefix in imports
5. **Production readiness** — would this survive real data?

## Rules

- **You write the code.** Coaching provides structure and explanation, not copy-paste solutions.
- **Ask why.** If something doesn't make sense, say so. Getting the explanation is the point.
- **Imports are not obvious.** If you need to import something you haven't used before, coaching will tell you what and explain what it does.
- **Small steps.** Each step should produce a runnable state. If tests break, we fix before moving on.
- **Debug first, ask second.** Read the error message. Most Python errors tell you exactly what's wrong and which line. Try to fix it yourself — post the error if you're stuck.
