import sys
import os
import asyncio
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.sqlite import SqliteSaver
# useful imports
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage

load_dotenv()
if not os.environ.get("ANTHROPIC_API_KEY"):
    print("environment variable ANTHROPIC_API_KEY not set")
    sys.exit(1)

# Custom state for agent
class MultiAgentState(TypedDict):
    question: str
    question_type: str
    answer: str
    feedback: str

question_category_prompt = '''You are a senior security operations analyst. Your task is to classify the incoming questions.
Depending on your answer, question will be routed to the right team, so your task is crucial for our team.
There are 3 possible question types:
- LOGS - questions related to logs stored in Elastic
- GRC - questions related to policy compliance including DORA and ISO27001
- AWS - questions related to AWS
Return in the output only one word (LOGS, GRC or AWS).
'''

def router_node(state: MultiAgentState):
    messages = [
        SystemMessage(content=question_category_prompt),
        HumanMessage(content=state['question'])
    ]
    model = ChatAnthropic(model="claude-3-5-sonnet-latest")
    response = model.invoke(messages)
    return {"question_type": response.content}

# Create the SQLite saver correctly
#memory = SqliteSaver(":memory:")  # Removed the .from_conn_string method

# Build the graph
builder = StateGraph(MultiAgentState)
builder.add_node("router", router_node)
builder.set_entry_point("router")
builder.add_edge('router', END)
graph = builder.compile()#checkpointer=memory)

# Test with different questions
thread = {"configurable": {"thread_id": "1"}}
for s in graph.stream({
    'question': "Please search elastic logs for events with PID 200?",
}, thread):
    print(s)

thread = {"configurable": {"thread_id": "2"}}
for s in graph.stream({
    'question': "What should a password policy look like with ISO27001 in mind?",
}, thread):
    print(s)

thread = {"configurable": {"thread_id": "3"}}
for s in graph.stream({
    'question': "How can I secure a public AWS bucket?",
}, thread):
    print(s)