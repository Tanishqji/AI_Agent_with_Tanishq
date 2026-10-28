"""
Simple Bug-Fixing Coding Agent (No LangGraph)
Uses Groq API with 3 tools:
- search_files
- search_in_file
- replace_line

Max retries: 3 attempts.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from groq import Groq

from tools import AVAILABLE_TOOLS, TOOLS_SCHEMA

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load .env by walking up to find .env if needed
current_dir = Path(__file__).resolve().parent
search_dir = current_dir
while search_dir != search_dir.parent:
    env_file = search_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        break
    search_dir = search_dir.parent

MODEL_NAME = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
MAX_ATTEMPTS = 3


def run_coding_agent(bug_description: str):
    """
    Executes the coding agent loop for a given bug description.
    Limits to MAX_ATTEMPTS turns.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("\n[ERROR] GROQ_API_KEY not found in environment variables. Please check your .env file.")
        return

    client = Groq(api_key=api_key)

    system_prompt = (
        "You are an expert coding agent that solves code bugs directly in files.\n"
        "You have access to 3 tools:\n"
        "1. search_files(query): Search and list files in the workspace.\n"
        "2. search_in_file(file_path, query): View lines with line numbers from a file.\n"
        "3. replace_line(file_path, line_number, new_line): Replace a specific line in a file.\n\n"
        "Rules:\n"
        "- If the user specifies the filename (e.g. 'sample.cpp'), call search_in_file directly without needing search_files.\n"
        "- Inspect the line numbers returned by search_in_file to find the exact line with the bug.\n"
        "- Use replace_line with the exact 1-indexed line number and corrected code.\n"
        "- You have a strict limit of 3 attempts. Once the replacement succeeds, explain your solution clearly."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please fix the following bug:\n{bug_description}"},
    ]

    print("\n" + "=" * 60)
    print("           CODING AGENT: STARTING BUG FIX")
    print("=" * 60)
    print(f"Bug Description: {bug_description}\n")

    attempt = 0
    solved = False
    replaced = False

    while attempt < MAX_ATTEMPTS:
        attempt += 1
        print(f"\n>>> [ATTEMPT {attempt}/{MAX_ATTEMPTS}] Contacting LLM...")

        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
                temperature=0.1,
            )
        except Exception as e:
            print(f"[ERROR] LLM API Call failed: {e}")
            break

        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None)

        # Case 1: No tool calls -> Agent has finished and provided final response
        if not tool_calls:
            print("\n" + "=" * 60)
            print("[SUCCESS] Bug Resolved!")
            print("Agent Explanation:")
            print(message.content or "The bug has been fixed.")
            print("=" * 60)
            solved = True
            break

        # Case 2: Agent decided to call one or more tools
        messages.append(message)

        for tc in tool_calls:
            func_name = tc.function.name
            raw_args = tc.function.arguments
            try:
                func_args = json.loads(raw_args)
            except Exception:
                func_args = {}

            print("\n------------------------------------------------------------")
            print(f"[TOOL CALLED]: {func_name}")
            print(f"[ARGUMENTS]  : {func_args}")
            print("------------------------------------------------------------")

            if func_name in AVAILABLE_TOOLS:
                tool_fn = AVAILABLE_TOOLS[func_name]
                try:
                    tool_result = tool_fn(**func_args)
                    if func_name == "replace_line" and "Success" in str(tool_result):
                        replaced = True
                except Exception as exc:
                    tool_result = f"Error executing {func_name}: {exc}"
            else:
                tool_result = f"Error: Tool '{func_name}' is not recognized."

            print(f"[TOOL RESULT]:\n{tool_result}\n")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": func_name,
                    "content": str(tool_result),
                }
            )

        # If replacement was executed successfully, request final explanation and conclude
        if replaced:
            try:
                final_res = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    temperature=0.1,
                )
                explanation = final_res.choices[0].message.content or "The bug has been successfully fixed."
                print("\n" + "=" * 60)
                print("[SUCCESS] Bug Resolved!")
                print("Agent Explanation:")
                print(explanation)
                print("=" * 60)
                solved = True
            except Exception:
                print("\n" + "=" * 60)
                print("[SUCCESS] Bug Resolved! Replacement applied successfully.")
                print("=" * 60)
                solved = True
            break

    if not solved:
        print("\n" + "=" * 60)
        print("[FAILED] Cannot solve the bug within the limit of 3 attempts.")
        print("=" * 60)


def main():
    print("=" * 60)
    print("           SIMPLE BUG FIXING CODING AGENT")
    print("=" * 60)
    print("Boilerplate file available: 'sample.cpp'")
    print("Introduce any bug into 'sample.cpp' and describe it below.")

    try:
        bug_desc = input("\nEnter your bug: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
        return

    if not bug_desc:
        print("No bug entered. Exiting.")
        return

    run_coding_agent(bug_desc)


if __name__ == "__main__":
    main()
