"""
Tool implementations for the Single-Agent and Multi-Agent systems.
Tools:
1. search: Web search tool (supports Wikipedia API + optional Tavily)
2. calculate: Safe mathematical expression evaluator
"""

import ast
import math
import operator as op
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# --- 1. SEARCH TOOL IMPLEMENTATION ---

def search(query: str) -> str:
    """
    Search for information using Wikipedia API or Tavily if configured.
    Returns concise summaries and facts.
    """
    # 1. Try Tavily if API key is present
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            res = client.search(query=query, max_results=3)
            results = res.get("results", [])
            if results:
                return "\n".join(f"- {r.get('title')}: {r.get('content')}" for r in results)
        except Exception:
            pass

    # 2. Wikipedia search API
    try:
        url = "https://en.wikipedia.org/w/api.php"
        headers = {"User-Agent": "ResearchAssistantBot/1.0 (https://example.com/bot; bot@example.org)"}
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 3,
        }
        resp = requests.get(url, params=params, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            search_items = data.get("query", {}).get("search", [])
            if search_items:
                output = []
                for item in search_items:
                    title = item.get("title", "")
                    snippet = item.get("snippet", "").replace('<span class="searchmatch">', "").replace("</span>", "")
                    page_text = snippet
                    try:
                        extract_params = {
                            "action": "query",
                            "prop": "extracts",
                            "exintro": True,
                            "explaintext": True,
                            "titles": title,
                            "format": "json",
                        }
                        extract_resp = requests.get(url, params=extract_params, headers=headers, timeout=5)
                        if extract_resp.status_code == 200:
                            pages = extract_resp.json().get("query", {}).get("pages", {})
                            for pid, pdata in pages.items():
                                ext = pdata.get("extract", "")
                                if ext:
                                    page_text = ext[:500].strip()
                                    break
                    except Exception:
                        pass
                    output.append(f"Title: {title}\nSummary: {page_text}")
                return "\n\n".join(output)
    except Exception:
        pass

    # 3. DuckDuckGo Instant Answer API fallback
    try:
        ddg_url = "https://api.duckduckgo.com/"
        ddg_params = {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
        ddg_resp = requests.get(ddg_url, params=ddg_params, timeout=6)
        if ddg_resp.status_code == 200:
            ddg_data = ddg_resp.json()
            abstract = ddg_data.get("AbstractText", "")
            if abstract:
                return f"DuckDuckGo Abstract: {abstract}"
    except Exception:
        pass

    return f"Search completed. Limited results found for query: '{query}'."


# --- 2. CALCULATE TOOL IMPLEMENTATION ---

_ALLOWED_OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}

_ALLOWED_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "pow": math.pow,
    "sum": sum,
}

def _evaluate_ast_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
        left = _evaluate_ast_node(node.left)
        right = _evaluate_ast_node(node.right)
        return _ALLOWED_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPERATORS:
        operand = _evaluate_ast_node(node.operand)
        return _ALLOWED_OPERATORS[type(node.op)](operand)
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_FUNCTIONS:
            fn = _ALLOWED_FUNCTIONS[node.func.id]
            args = [_evaluate_ast_node(arg) for arg in node.args]
            return fn(*args)
    raise ValueError(f"Unsupported math operation: {ast.dump(node)}")


def calculate(expression: str) -> str:
    """
    Safely evaluate a mathematical expression using AST parsing.
    Supports addition (+), subtraction (-), multiplication (*), division (/),
    exponents (**), modulo (%), and helper functions (round, abs, sqrt).
    """
    try:
        clean_expr = expression.strip().replace(",", "")
        tree = ast.parse(clean_expr, mode="eval")
        result = _evaluate_ast_node(tree.body)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return str(result)
    except Exception as e:
        return f"Error evaluating expression '{expression}': {str(e)}"


# --- 3. TOOL SCHEMAS FOR OPENAI / GROQ TOOL CALLING ---

SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search",
        "description": "Search the web/encyclopedia for factual information, statistics, dates, or population data.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The specific query to search for.",
                }
            },
            "required": ["query"],
        },
    },
}

CALCULATE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "calculate",
        "description": "Perform mathematical and arithmetic calculations (e.g., '(37400000 + 32900000)', 'round(1234.56, 2)', '(x / y) * 100').",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate.",
                }
            },
            "required": ["expression"],
        },
    },
}

AVAILABLE_TOOLS = {
    "search": search,
    "calculate": calculate,
}
