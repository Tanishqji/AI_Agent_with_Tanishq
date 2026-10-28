# Week 6 Day 20: Single-Agent vs. Multi-Agent System (Without LangGraph)

This project compares two agent architectures for multi-step reasoning, tool execution, and token efficiency:
1. **Single-Agent System**: A unified LLM agent that dynamically decides which tools to invoke (`search`, `calculate`) and how many times, with a limit of 5 attempts.
2. **Multi-Agent System (No LangGraph)**: A modular pure-Python multi-agent system comprising three specialized LLMs:
   - **Manager LLM** (`ask_manager_llm`): Decides which helper LLM to call next or synthesizes the final answer.
   - **Search LLM** (`ask_search_llm`): Access *only* to the `search` tool.
   - **Maths LLM** (`ask_maths_llm`): Access *only* to the `calculate` tool.
   - **Notes File** (`manager_notes.txt`): Shared memory file where the manager tracks findings and responses from helper LLMs.

Both systems track precise **token usage** (Prompt, Completion, Total) to evaluate architectural trade-offs.

---

## Architecture Overview

```
                      +-----------------------------+
                      |       USER COMPLEX QUERY    |
                      +-----------------------------+
                                     |
           +-------------------------+-------------------------+
           |                                                   |
           v                                                   v
+-------------------------+                       +-------------------------+
|   SINGLE-AGENT SYSTEM   |                       |    MULTI-AGENT SYSTEM   |
|   (One LLM, 2 Tools)    |                       |     (Without LangGraph) |
+-------------------------+                       +-------------------------+
| - Tools: search + calc  |                       | 1. Manager LLM:         |
| - Loops up to 5 attempts|                       |    Orchestration only   |
| - Monolithic chat state |                       |    Reads/writes notes   |
+-------------------------+                       | 2. Search LLM:          |
           |                                      |    Only 'search' tool   |
           |                                      | 3. Maths LLM:           |
           |                                      |    Only 'calculate' tool|
           |                                      +-------------------------+
           |                                                   |
           +-------------------------+-------------------------+
                                     |
                                     v
                       +---------------------------+
                       | TOKEN USAGE COMPARISON    |
                       +---------------------------+
```

---

## File Structure

| File | Description |
| :--- | :--- |
| [`tools.py`](tools.py) | Definitions and schemas for `search` (Wikipedia API + DuckDuckGo fallback) and `calculate` (safe AST arithmetic evaluator). |
| [`single_agent.py`](single_agent.py) | Single-agent autonomous loop with max 5 attempts and token usage tracking. |
| [`multi_agent.py`](multi_agent.py) | Multi-agent system implementing `ask_manager_llm`, `ask_search_llm`, `ask_maths_llm`, `manager_notes.txt` tracking, and per-agent token accounting. |
| [`manager_notes.txt`](manager_notes.txt) | File where the manager LLM tracks helper agent findings across execution cycles. |
| [`main.py`](main.py) | Benchmark runner executing both systems on complex multi-step queries and outputting comparative token metrics. |
| [`pyproject.toml`](pyproject.toml) | Dependencies (`groq`, `python-dotenv`, `requests`). |

---

## Benchmark Query

The benchmark evaluates both architectures on a multi-step query requiring information retrieval and chained arithmetic:

> *"Search for the current approximate populations of Tokyo and Delhi. Then calculate: 1) their combined total population, 2) the difference between Tokyo's and Delhi's population, and 3) what percentage of that combined total Tokyo accounts for."*

---

## Benchmark Results & Token Comparison

| System Architecture | Prompt Tokens | Completion Tokens | Total Tokens | Cycles / Attempts |
| :--- | :---: | :---: | :---: | :---: |
| **Single Agent** | 9,068 | 794 | **9,862** | 5 |
| **Multi-Agent System** | 15,369 | 1,789 | **17,158** | 4 |

### Multi-Agent Token Breakdown

| Agent Component | Prompt Tokens | Completion Tokens | Total Tokens |
| :--- | :---: | :---: | :---: |
| **Manager LLM** | 3,601 | 442 | 4,043 |
| **Search LLM** | 9,660 | 964 | 10,624 |
| **Maths LLM** | 2,108 | 383 | 2,491 |
| **Combined** | **15,369** | **1,789** | **17,158** |

---

## Key Insights & Architectural Analysis

1. **Why Single-Agent Used Fewer Tokens (+74% token efficiency on short/medium tasks):**
   - The single agent maintains a single conversation state. It calls tools and receives tool results in the same thread without manager orchestration prompts, delegation instructions, or JSON formatting schemas.
   - However, conversation history in a single agent grows monotonically. On tasks with dozens of iterations, resending massive history every turn can become very costly.

2. **Why Multi-Agent Provides Higher Reliability Despite More Tokens:**
   - **Role Specialization:** The Manager does not get overwhelmed by raw tool schemas or extensive search snippets; it only reads high-level summaries from `manager_notes.txt`.
   - **Tool Isolation:** The Maths LLM only sees calculation tools (preventing hallucinations or searching for math), while the Search LLM only sees search tools.
   - **Quality of Execution:** Single-agent reached its 5-turn limit and barely completed the calculations. The Multi-Agent system systematically searched, refined estimates, delegated exact math to the calculation specialist, and produced a structured, verified synthesis.

---

## How to Run

### 1. Run the Benchmark
```bash
python main.py
```

### 2. Run with Custom Query
```bash
python main.py --query "Search for GDP of France and Germany, then calculate the difference and France's percentage of total."
```

### 3. Run in Interactive Mode
```bash
python main.py --interactive
```
