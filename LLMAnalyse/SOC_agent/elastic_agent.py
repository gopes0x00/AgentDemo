import os
import sys
import sqlite3
import asyncio
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from IPython.display import Image


# ENV
load_dotenv()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", None)
ES_API_KEY = os.environ.get("ES_API_KEY", None)

if ANTHROPIC_API_KEY is None or ES_API_KEY is None :
    print("environment variables missing")
    sys.exit(1)

# Create the SQLite saver correctly
conn = sqlite3.connect(':memory:', check_same_thread=False)
checkpointer = SqliteSaver(conn)

elastic_expert_system_prompt = """"""


def execute_elastic_audit_query(query: str) -> dict:
    """Takes a string and runs an elastic query"""
    return {"results": f"No results found for query: {query}"}

class AgentState(TypedDict):
    question: str
    answer: str

async def call_model(state: AgentState):
    agent = create_react_agent(
        model = ChatAnthropic(model="claude-3-5-sonnet-latest"),
        tools=[execute_elastic_audit_query],
        prompt="You are a helpful assistant",
        checkpointer=checkpointer,
    )
    messages = [HumanMessage(content=state['question'])]
    result = agent.ainvoke({"messages": messages})
    return result


workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.set_entry_point("agent")

# Now we can compile and visualize our graph
graph = workflow.compile()

try:
    Image(graph.get_graph().draw_png())
except Exception:
    # This requires some extra dependencies and is optional
    pass

async def execute():
    config = {"configurable": {"thread_id": "1"}}
    state = AgentState(question="Run a query for the search term whoami")
    async for chunk in graph.astream(state, config=config, stream_mode="updates"):
        v = next(iter(chunk.values()))
        v["messages"][-1].pretty_print()

if __name__ == "__main__":
    asyncio.run(execute())