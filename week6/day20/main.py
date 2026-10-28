"""
Week 6 Day 20: Single Agent vs. Multi-Agent System (Without LangGraph)
Token Usage Evaluation and Comparison

Architecture:
1. Single-Agent:
   - One LLM loop with access to both 'search' and 'calculate' tools.
   - Max 5 attempts.
   - Tracks token usage.

2. Multi-Agent:
   - ask_manager_llm: Orchestrator deciding which helper agent to invoke.
   - ask_search_llm: Specializes in web search (only 'search' tool).
   - ask_maths_llm: Specializes in calculations (only 'calculate' tool).
   - Notes file ('manager_notes.txt') tracking helper responses.
   - Per-agent and aggregated token tracking.
"""

import argparse
import os
import sys
from dotenv import load_dotenv

from multi_agent import MultiAgentSystem
from single_agent import SingleAgent

# Ensure UTF-8 console output for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

DEFAULT_COMPLEX_QUERY = (
    "Search for the current approximate populations of Tokyo and Delhi. "
    "Then calculate: "
    "1) their combined total population, "
    "2) the difference between Tokyo's and Delhi's population, and "
    "3) what percentage of that combined total Tokyo accounts for."
)


def print_divider(title: str = "", char: str = "=", length: int = 80):
    if title:
        padding = (length - len(title) - 2) // 2
        print(f"\n{char * padding} {title} {char * padding}")
    else:
        print(char * length)


def run_benchmark(query: str):
    print_divider("WEEK 6 DAY 20: SINGLE-AGENT VS MULTI-AGENT BENCHMARK")
    print(f"Target Complex Query:\n  \"{query}\"\n")

    # 1. RUN SINGLE-AGENT SYSTEM
    print_divider("1. RUNNING SINGLE-AGENT SYSTEM", "-")
    single_agent = SingleAgent()
    single_res = single_agent.run(query)

    print("\n[Single-Agent Execution Trace]:")
    for step in single_res["trace"]:
        print(f"  {step}")

    print("\n[Single-Agent Final Answer]:")
    print(single_res["answer"].strip())

    print("\n[Single-Agent Token Usage]:")
    print(f"  Prompt Tokens:     {single_res['token_usage']['prompt_tokens']}")
    print(f"  Completion Tokens: {single_res['token_usage']['completion_tokens']}")
    print(f"  Total Tokens:      {single_res['token_usage']['total_tokens']}")

    # 2. RUN MULTI-AGENT SYSTEM
    print_divider("2. RUNNING MULTI-AGENT SYSTEM (NO LANGGRAPH)", "-")
    multi_agent = MultiAgentSystem()
    multi_res = multi_agent.run(query)

    print("\n[Multi-Agent Execution Trace]:")
    for step in multi_res["trace"]:
        print(f"  {step}")

    print("\n[Multi-Agent Final Answer]:")
    print(multi_res["answer"].strip())

    print("\n[Multi-Agent Token Usage Breakdown]:")
    m_usage = multi_res["token_usage"]
    print(f"  Manager LLM:    Prompt={m_usage['manager']['prompt_tokens']}, "
          f"Completion={m_usage['manager']['completion_tokens']}, "
          f"Total={m_usage['manager']['total_tokens']}")
    print(f"  Search LLM:     Prompt={m_usage['search_llm']['prompt_tokens']}, "
          f"Completion={m_usage['search_llm']['completion_tokens']}, "
          f"Total={m_usage['search_llm']['total_tokens']}")
    print(f"  Maths LLM:      Prompt={m_usage['maths_llm']['prompt_tokens']}, "
          f"Completion={m_usage['maths_llm']['completion_tokens']}, "
          f"Total={m_usage['maths_llm']['total_tokens']}")
    print(f"  -------------------------------------------------------------")
    print(f"  Combined Total: Prompt={m_usage['total']['prompt_tokens']}, "
          f"Completion={m_usage['total']['completion_tokens']}, "
          f"Total={m_usage['total']['total_tokens']}")

    print("\n[Manager Notes File Content]:")
    if os.path.exists(multi_res["notes_file"]):
        with open(multi_res["notes_file"], "r", encoding="utf-8") as f:
            print(f.read().strip())

    # 3. COMPARATIVE ANALYSIS
    print_divider("3. COMPARATIVE TOKEN USAGE & ARCHITECTURE ANALYSIS")
    single_tot = single_res["token_usage"]["total_tokens"]
    multi_tot = multi_res["token_usage"]["total"]["total_tokens"]

    print(f"{'System Architecture':<22} | {'Prompt':<10} | {'Completion':<12} | {'Total Tokens':<12} | {'Attempts':<8}")
    print("-" * 75)
    print(f"{'Single Agent':<22} | {single_res['token_usage']['prompt_tokens']:<10} | "
          f"{single_res['token_usage']['completion_tokens']:<12} | "
          f"{single_tot:<12} | {single_res['attempts_used']:<8}")
    print(f"{'Multi-Agent System':<22} | {m_usage['total']['prompt_tokens']:<10} | "
          f"{m_usage['total']['completion_tokens']:<12} | "
          f"{multi_tot:<12} | {multi_res['attempts_used']:<8}")
    print("-" * 75)

    if multi_tot > single_tot:
        diff = multi_tot - single_tot
        pct = (diff / single_tot) * 100 if single_tot else 0
        winner = f"Single-Agent used FEWER tokens (Multi-Agent used {diff} more tokens, +{pct:.1f}%)."
    elif single_tot > multi_tot:
        diff = single_tot - multi_tot
        pct = (diff / multi_tot) * 100 if multi_tot else 0
        winner = f"Multi-Agent used FEWER tokens (Single-Agent used {diff} more tokens, +{pct:.1f}%)."
    else:
        winner = "Both systems used the exact same amount of tokens."

    print(f"\nVerdict: {winner}\n")
    print("Architectural Analysis:")
    print("1. Single-Agent Pros & Cons:")
    print("   - Single prompt context where conversation history grows monotonically.")
    print("   - In long loops, resending the entire message history (all previous tool inputs & outputs)")
    print("     can lead to rapid prompt token accumulation.")
    print("2. Multi-Agent Pros & Cons:")
    print("   - Separates concerns: Helper agents get focused sub-prompts and isolated tool contexts.")
    print("   - Manager uses a compact 'notes file' instead of raw full chat history.")
    print("   - However, each manager orchestration turn incurs overhead (orchestration system prompts")
    print("     and JSON formatting). For short tasks, this overhead makes multi-agent consume more tokens,")
    print("     while for very large workflows, modular context isolation saves tokens.")
    print_divider()


def main():
    parser = argparse.ArgumentParser(description="Week 6 Day 20 Single vs Multi-Agent Benchmark")
    parser.add_argument("--query", "-q", type=str, default=DEFAULT_COMPLEX_QUERY, help="Query to run")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run interactive mode")
    args = parser.parse_args()

    if args.interactive:
        user_input = input("Enter complex query: ").strip()
        query = user_input if user_input else DEFAULT_COMPLEX_QUERY
    else:
        query = args.query

    run_benchmark(query)


if __name__ == "__main__":
    main()
