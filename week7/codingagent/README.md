# Simple Bug-Fixing Coding Agent (Week 7)

A lightweight, simple coding agent built with **Groq** (without LangGraph) to locate and fix bugs in code files.

---

## Features

1. **Simple 3-Tool Arsenal**:
   - `search_files(query)`: Finds relevant file paths in the workspace.
   - `search_in_file(file_path, query)`: Reads a file and returns content with 1-indexed line numbers.
   - `replace_line(file_path, line_number, new_line)`: Replaces a specific line in a file with the corrected code.

2. **Step-by-Step Transparency**:
   - Logs every tool call, its parameters, and the returned output at each attempt so you can inspect the exact agent workflow.

3. **Strict 3-Attempt Retry Limit**:
   - The agent has a maximum of 3 attempts to locate and fix the bug.
   - If it cannot solve the bug within 3 attempts, it cleanly prints:
     `[FAILED] Cannot solve the bug within the limit of 3 attempts.`

4. **Interactive CLI**:
   - When run, it immediately prompts: `Enter your bug:` in plain English and begins working autonomously.

---

## File Structure

- [`sample.cpp`](sample.cpp): Boilerplate C++ file without any initial bugs (for you to test by introducing bugs).
- [`tools.py`](tools.py): Implementation and schemas for `search_files`, `search_in_file`, and `replace_line`.
- [`main.py`](main.py): The coding agent loop and CLI entry point.
- [`pyproject.toml`](pyproject.toml): Project dependencies (`groq`, `python-dotenv`).

---

## How to Test

1. Open [`sample.cpp`](sample.cpp) and introduce a bug of your choice (e.g. change line 5 from `return a + b;` to `return a - b;`).
2. Run the agent in your terminal:
   ```bash
   python main.py
   ```
3. Type your bug description in simple English when prompted:
   ```text
   Enter your bug: In sample.cpp the add function is subtracting instead of adding. Fix it.
   ```
4. Watch the agent inspect the file, locate line numbers, execute the replacement, and report the fix!
