from typing import TypedDict
import langgraph.graph


# 1. State
class State(TypedDict):
    number: int


# 2. Nodes
def double(state: State) -> State:
    new_value = state["number"] * 2
    print(f"Doubling: {state['number']} -> {new_value}")
    return {"number": new_value}


def finish(state: State) -> State:
    print(f"Finished with value: {state['number']}")
    return state


# 3. Decision (conditional edge function)
def decision(state: State) -> str:
    if state["number"] >= 100:
        return "finish"
    return "double"


# 4. Build the graph
builder = langgraph.graph.StateGraph(State)

builder.add_node("double", double)
builder.add_node("finish", finish)

builder.set_entry_point("double")

builder.add_conditional_edges(
    "double",
    decision,
    {
        "double": "double",   # loop back and keep doubling
        "finish": "finish",   # stop when >= 100
    },
)

builder.add_edge("finish", langgraph.graph.END)

graph = builder.compile()


# 5. Run
result = graph.invoke({"number": 5})
print("Final result:", result)
