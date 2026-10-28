"""
Multi-Agent System (without LangGraph).
Contains three distinct LLM functions:
1. ask_manager_llm: Orchestrator whose only job is to decide which helper LLM to use or finalize.
2. ask_search_llm: Dedicated search specialist with access ONLY to the 'search' tool.
3. ask_maths_llm: Dedicated math specialist with access ONLY to the 'calculate' tool.

The manager LLM maintains a notes file ('manager_notes.txt') tracking helper LLM findings.
Comprehensive token usage is tracked across each agent and overall.
"""

import json
import os
import sys
from typing import Any, Dict, List
from dotenv import load_dotenv
from groq import Groq

from tools import AVAILABLE_TOOLS, CALCULATE_TOOL_SCHEMA, SEARCH_TOOL_SCHEMA

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

MODEL_NAME = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
NOTES_FILE_PATH = os.path.join(os.path.dirname(__file__), "manager_notes.txt")
MAX_MANAGER_ATTEMPTS = 5


class MultiAgentSystem:
    def __init__(self, model: str = MODEL_NAME, notes_file: str = NOTES_FILE_PATH):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables.")
        self.client = Groq(api_key=api_key)
        self.model = model
        self.notes_file = notes_file

        # Per-agent token tracking
        self.usage_manager = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.usage_search = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.usage_maths = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _track(self, category: str, usage):
        if not usage:
            return
        target = {
            "manager": self.usage_manager,
            "search": self.usage_search,
            "maths": self.usage_maths,
        }.get(category)

        if target is not None:
            target["prompt_tokens"] += getattr(usage, "prompt_tokens", 0) or 0
            target["completion_tokens"] += getattr(usage, "completion_tokens", 0) or 0
            target["total_tokens"] += getattr(usage, "total_tokens", 0) or 0

    # --- NOTES FILE HELPERS ---

    def _init_notes(self, user_query: str):
        with open(self.notes_file, "w", encoding="utf-8") as f:
            f.write(f"# MANAGER NOTES\nInitial User Goal: {user_query}\n\n")

    def _read_notes(self) -> str:
        if os.path.exists(self.notes_file):
            with open(self.notes_file, "r", encoding="utf-8") as f:
                return f.read()
        return "Notes file is empty."

    def _append_to_notes(self, role: str, subtask: str, response: str):
        with open(self.notes_file, "a", encoding="utf-8") as f:
            f.write(f"--- Note from [{role}] ---\n")
            f.write(f"Assigned Subtask: {subtask}\n")
            f.write(f"Findings/Result:\n{response.strip()}\n\n")

    # --- 1. MANAGER LLM ---

    def ask_manager_llm(self, user_query: str, notes_content: str) -> Dict[str, str]:
        """
        Manager LLM: Decides which helper LLM to invoke or produces the final answer.
        Does not execute search or math tools directly.
        """
        system_prompt = (
            "You are the Manager LLM. Your ONLY job is to manage the problem-solving process.\n"
            "You have two helper LLMs at your disposal:\n"
            "1. 'search_llm': Has access ONLY to the search tool. Use for looking up data, populations, statistics, facts.\n"
            "2. 'maths_llm': Has access ONLY to the calculate tool. Use for arithmetic, totals, differences, percentages.\n\n"
            "Review the user query and your current notes file carefully.\n"
            "- If factual data is missing, delegate to 'search_llm'.\n"
            "- If calculations are needed on gathered data, delegate to 'maths_llm'.\n"
            "- If all facts and calculations are complete, output 'final_answer'.\n\n"
            "You MUST respond ONLY with valid JSON in this exact structure:\n"
            "{\n"
            '  "decision": "search_llm" | "maths_llm" | "final_answer",\n'
            '  "instruction": "<Specific question/task for the helper agent, OR the full final answer for user>"\n'
            "}"
        )

        user_content = (
            f"Original User Query:\n{user_query}\n\n"
            f"Current Manager Notes File:\n{notes_content}\n\n"
            "What is your next decision? Return valid JSON only."
        )

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        self._track("manager", resp.usage)
        raw_text = resp.choices[0].message.content or "{}"
        try:
            return json.loads(raw_text)
        except Exception:
            return {"decision": "final_answer", "instruction": raw_text}

    # --- 2. SEARCH LLM ---

    def ask_search_llm(self, subtask: str) -> str:
        """
        Search LLM: Has access ONLY to the search tool.
        Finds factual information and provides a clear summary.
        """
        system_prompt = (
            "You are the Search LLM helper agent.\n"
            "Your role is exclusively to search the encyclopedia/web for accurate facts and statistics.\n"
            "You have access ONLY to the 'search' tool.\n"
            "Always invoke the 'search' tool to retrieve information. Once you receive the tool response, "
            "summarize the essential numbers and facts concisely."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": subtask},
        ]

        # Tool execution loop for search
        for _ in range(3):
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=[SEARCH_TOOL_SCHEMA],
                tool_choice="auto",
                temperature=0.1,
            )
            self._track("search", resp.usage)
            msg = resp.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None)

            if not tool_calls:
                return msg.content or "No search information found."

            messages.append(msg)
            for tc in tool_calls:
                func_args = {}
                try:
                    func_args = json.loads(tc.function.arguments)
                except Exception:
                    pass
                result = AVAILABLE_TOOLS["search"](**func_args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": "search",
                        "content": str(result),
                    }
                )

        # Fallback final synthesis
        final_resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages + [{"role": "user", "content": "Please summarize the search findings now."}],
            temperature=0.1,
        )
        self._track("search", final_resp.usage)
        return final_resp.choices[0].message.content or ""

    # --- 3. MATHS LLM ---

    def ask_maths_llm(self, subtask: str) -> str:
        """
        Maths LLM: Has access ONLY to the calculate tool.
        Performs arithmetic, percentages, and numerical computations.
        """
        system_prompt = (
            "You are the Maths LLM helper agent.\n"
            "Your role is exclusively to perform mathematical calculations and arithmetic operations.\n"
            "You have access ONLY to the 'calculate' tool.\n"
            "Always use the 'calculate' tool to evaluate mathematical expressions rather than computing in your head.\n"
            "Provide the calculated numbers and clear arithmetic steps."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": subtask},
        ]

        # Tool execution loop for maths
        for _ in range(3):
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=[CALCULATE_TOOL_SCHEMA],
                tool_choice="auto",
                temperature=0.1,
            )
            self._track("maths", resp.usage)
            msg = resp.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None)

            if not tool_calls:
                return msg.content or "No calculation result returned."

            messages.append(msg)
            for tc in tool_calls:
                func_args = {}
                try:
                    func_args = json.loads(tc.function.arguments)
                except Exception:
                    pass
                result = AVAILABLE_TOOLS["calculate"](**func_args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": "calculate",
                        "content": str(result),
                    }
                )

        # Fallback final synthesis
        final_resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages + [{"role": "user", "content": "Please present the final calculation results."}],
            temperature=0.1,
        )
        self._track("maths", final_resp.usage)
        return final_resp.choices[0].message.content or ""

    # --- MULTI-AGENT ORCHESTRATION LOOP ---

    def run(self, query: str) -> Dict[str, Any]:
        """
        Runs the multi-agent orchestration loop.
        The manager reads notes, decides on helper agent, appends results, and synthesizes the answer.
        """
        self._init_notes(query)
        trace = []
        final_answer = ""
        attempt = 0

        while attempt < MAX_MANAGER_ATTEMPTS:
            attempt += 1
            trace.append(f"\n--- [Manager Cycle {attempt}/{MAX_MANAGER_ATTEMPTS}] ---")

            notes_content = self._read_notes()
            decision_data = self.ask_manager_llm(query, notes_content)

            decision = decision_data.get("decision", "final_answer").lower()
            instruction = decision_data.get("instruction", "")

            trace.append(f"[Manager Decision]: {decision.upper()}")
            trace.append(f"[Manager Instruction/Subtask]: {instruction}")

            if "search" in decision:
                trace.append("[Invoking Helper]: ask_search_llm")
                helper_resp = self.ask_search_llm(instruction)
                trace.append(f"[Search LLM Response Preview]: {helper_resp[:160]}...")
                self._append_to_notes("search_llm", instruction, helper_resp)

            elif "math" in decision:
                trace.append("[Invoking Helper]: ask_maths_llm")
                helper_resp = self.ask_maths_llm(instruction)
                trace.append(f"[Maths LLM Response Preview]: {helper_resp[:160]}...")
                self._append_to_notes("maths_llm", instruction, helper_resp)

            elif "final" in decision:
                final_answer = instruction
                trace.append("[Manager Concluded]: Final answer synthesized.")
                break
            else:
                final_answer = instruction
                break

        # Fallback if manager exceeded max attempts without explicit final answer
        if not final_answer:
            notes_content = self._read_notes()
            final_answer = f"Summary based on Manager Notes:\n{notes_content}"
            trace.append("[Manager Cycle]: Final answer generated from accumulated notes.")

        total_tokens = (
            self.usage_manager["total_tokens"]
            + self.usage_search["total_tokens"]
            + self.usage_maths["total_tokens"]
        )
        total_prompt = (
            self.usage_manager["prompt_tokens"]
            + self.usage_search["prompt_tokens"]
            + self.usage_maths["prompt_tokens"]
        )
        total_completion = (
            self.usage_manager["completion_tokens"]
            + self.usage_search["completion_tokens"]
            + self.usage_maths["completion_tokens"]
        )

        return {
            "system": "Multi-Agent",
            "query": query,
            "answer": final_answer,
            "attempts_used": attempt,
            "notes_file": self.notes_file,
            "token_usage": {
                "manager": self.usage_manager,
                "search_llm": self.usage_search,
                "maths_llm": self.usage_maths,
                "total": {
                    "prompt_tokens": total_prompt,
                    "completion_tokens": total_completion,
                    "total_tokens": total_tokens,
                },
            },
            "trace": trace,
        }
