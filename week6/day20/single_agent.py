"""
Single-Agent Implementation.
A single LLM agent has access to both 'search' and 'calculate' tools.
It dynamically chooses which tools to use and how many times, up to a max attempts of 5.
Tracks token usage across all LLM calls.
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
MAX_ATTEMPTS = 5


class SingleAgent:
    def __init__(self, model: str = MODEL_NAME):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables.")
        self.client = Groq(api_key=api_key)
        self.model = model
        self.tools = [SEARCH_TOOL_SCHEMA, CALCULATE_TOOL_SCHEMA]
        self.token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    def _track_usage(self, usage):
        if usage:
            self.token_usage["prompt_tokens"] += getattr(usage, "prompt_tokens", 0) or 0
            self.token_usage["completion_tokens"] += getattr(usage, "completion_tokens", 0) or 0
            self.token_usage["total_tokens"] += getattr(usage, "total_tokens", 0) or 0

    def ask_llm(self, messages: List[Dict[str, Any]]) -> Any:
        """Single LLM invocation with tool calling support."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tools,
            tool_choice="auto",
            temperature=0.1,
        )
        self._track_usage(response.usage)
        return response.choices[0].message

    def run(self, query: str) -> Dict[str, Any]:
        """
        Runs the agentic loop up to MAX_ATTEMPTS times.
        The LLM decides tools and turns autonomously.
        """
        system_prompt = (
            "You are an autonomous AI research and computation agent.\n"
            "You have access to two tools:\n"
            "1. 'search': for finding factual data, statistics, populations, or figures.\n"
            "2. 'calculate': for evaluating math expressions, percentages, totals, and differences.\n"
            "Guidelines:\n"
            "- Always use 'search' when factual data is needed.\n"
            "- Once you find reasonable demographic or statistical estimates, do not keep looping searches—proceed to use 'calculate' to compute the required figures.\n"
            "- Always use 'calculate' for exact mathematical evaluations rather than estimating in your head.\n"
            "- When you have gathered the data and performed all calculations, provide a clear, comprehensive final answer."
        )

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        trace = []
        final_answer = ""
        attempt = 0

        while attempt < MAX_ATTEMPTS:
            attempt += 1
            trace.append(f"\n--- [Single Agent] Attempt {attempt}/{MAX_ATTEMPTS} ---")

            message = self.ask_llm(messages)
            tool_calls = getattr(message, "tool_calls", None)

            # If no tool calls, the model gave its final answer
            if not tool_calls:
                final_answer = message.content or ""
                trace.append(f"[Single Agent] Generated final answer without further tool calls.")
                break

            # LLM decided to call tools
            messages.append(message)
            for tool_call in tool_calls:
                func_name = tool_call.function.name
                func_args_str = tool_call.function.arguments
                try:
                    func_args = json.loads(func_args_str)
                except Exception:
                    func_args = {}

                trace.append(f"[Single Agent Tool Call] {func_name}({func_args})")

                if func_name in AVAILABLE_TOOLS:
                    fn = AVAILABLE_TOOLS[func_name]
                    try:
                        result = fn(**func_args)
                    except Exception as exc:
                        result = f"Error executing {func_name}: {exc}"
                else:
                    result = f"Error: Tool '{func_name}' is not recognized."

                trace.append(f"[Single Agent Tool Result Preview]: {str(result)[:150]}...")

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": func_name,
                        "content": str(result),
                    }
                )

        # If max attempts reached without final text, request a final synthesis
        if not final_answer:
            messages.append(
                {
                    "role": "user",
                    "content": "Please synthesize the final answer based on all tool results so far.",
                }
            )
            final_msg = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
            )
            self._track_usage(final_msg.usage)
            final_answer = final_msg.choices[0].message.content or ""
            trace.append("[Single Agent] Synthesized final answer after max attempts reached.")

        return {
            "system": "Single-Agent",
            "query": query,
            "answer": final_answer,
            "attempts_used": attempt,
            "token_usage": self.token_usage,
            "trace": trace,
        }
