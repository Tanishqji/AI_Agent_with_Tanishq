"""
Tools for the Coding Agent:
1. search_files: Lists files in the directory matching a query/extension.
2. search_in_file: Shows lines with line numbers for a given file or search query.
3. replace_line: Replaces a specific line in a file with a new line.
"""

import os
from pathlib import Path

EXCLUDED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".idea", ".vscode"}


def search_files(query: str = "") -> str:
    """
    Search and list files in the current workspace directory.
    If query is provided, filters for files containing query in their name.
    """
    matches = []
    base_path = Path(".")
    for root, dirs, files in os.walk(base_path):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            rel_path = os.path.relpath(os.path.join(root, f), base_path)
            # Normalize path for readability
            rel_path = rel_path.replace("\\", "/")
            if not query or query.lower() in rel_path.lower():
                matches.append(rel_path)

    if not matches:
        return f"No files found matching '{query}'."
    return "\n".join(matches)


def search_in_file(file_path: str, query: str = "") -> str:
    """
    Reads a file and returns its content with 1-indexed line numbers.
    If query is provided, returns matching lines and surrounding lines with their line numbers.
    If query is empty, returns all lines with their line numbers.
    """
    if not os.path.exists(file_path):
        return f"Error: File '{file_path}' does not exist."

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return f"Error reading file '{file_path}': {e}"

    if not lines:
        return f"File '{file_path}' is empty."

    # For files up to 100 lines, return the complete file with line numbers
    if len(lines) <= 100 or not query:
        numbered_lines = [f"Line {idx}: {line.rstrip()}" for idx, line in enumerate(lines, start=1)]
        return f"Content of '{file_path}' with line numbers:\n" + "\n".join(numbered_lines)

    # For larger files, return matching lines with surrounding context (5 lines before and after)
    matching_indices = set()
    for idx, line in enumerate(lines, start=1):
        if query.lower() in line.lower():
            start = max(1, idx - 4)
            end = min(len(lines), idx + 5)
            for i in range(start, end + 1):
                matching_indices.add(i)

    if not matching_indices:
        return f"No matches found for '{query}' in '{file_path}'."

    sorted_indices = sorted(matching_indices)
    output = [f"Matches and context for '{query}' in '{file_path}':"]
    prev = None
    for idx in sorted_indices:
        if prev is not None and idx > prev + 1:
            output.append("  ...")
        output.append(f"Line {idx}: {lines[idx - 1].rstrip()}")
        prev = idx

    return "\n".join(output)


def replace_line(file_path: str, line_number: int, new_line: str) -> str:
    """
    Replaces a specific line (1-indexed) in a file with new_line.
    """
    if not os.path.exists(file_path):
        return f"Error: File '{file_path}' does not exist."

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return f"Error reading file '{file_path}': {e}"

    total_lines = len(lines)
    if line_number < 1 or line_number > total_lines:
        return f"Error: Line number {line_number} is out of range. File has {total_lines} lines."

    old_line = lines[line_number - 1].rstrip()
    # Preserve original indentation if new_line does not specify any
    leading_ws = len(old_line) - len(old_line.lstrip())
    if leading_ws > 0 and not new_line.startswith((" ", "\t")):
        new_line = (" " * leading_ws) + new_line

    # Ensure new_line ends with newline character
    if not new_line.endswith("\n"):
        new_line_with_nl = new_line + "\n"
    else:
        new_line_with_nl = new_line

    lines[line_number - 1] = new_line_with_nl

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        return f"Error writing to file '{file_path}': {e}"

    return (
        f"Success: Replaced line {line_number} in '{file_path}'.\n"
        f"Old line: '{old_line}'\n"
        f"New line: '{new_line.rstrip()}'"
    )


# --- Tool schemas for Groq / OpenAI tool calling ---

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Lists paths of files in the project workspace related to the bug or matching a search query/extension.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optional search term or file extension (e.g. 'cpp' or 'sample').",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_file",
            "description": "Searches inside a file and returns lines with their 1-indexed line numbers. If query is empty, returns all lines with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The relative path of the file to inspect (e.g. 'sample.cpp').",
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional search term to find specific lines, or empty to read the whole file.",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_line",
            "description": "Replaces a specific 1-indexed line number in a file with the new code line to fix a bug.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to modify.",
                    },
                    "line_number": {
                        "type": "integer",
                        "description": "The 1-indexed line number to replace.",
                    },
                    "new_line": {
                        "type": "string",
                        "description": "The new replacement line of code.",
                    },
                },
                "required": ["file_path", "line_number", "new_line"],
            },
        },
    },
]

AVAILABLE_TOOLS = {
    "search_files": search_files,
    "search_in_file": search_in_file,
    "replace_line": replace_line,
}
