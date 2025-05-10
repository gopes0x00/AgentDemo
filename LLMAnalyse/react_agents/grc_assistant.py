import sys
import os
from dotenv import load_dotenv
from langchain_tavily import TavilySearch
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic


# Load in the API keys
load_dotenv()

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("environment variable ANTHROPIC_API_KEY not set")
    sys.exit(1)

if not os.environ.get("TAVILY_API_KEY"):
    print("environment variable TAVILY_API_KEYILY not set")
    sys.exit(1)


# Configure the model - this can be done in multiple ways
model = ChatAnthropic(model="claude-3-5-sonnet-latest")

# Initialise search tool
tavily_search_tool = TavilySearch(
    max_results=5,
    topic="general"
)

# Create the react agent and pass it tools and prompt
agent = create_react_agent(
    model,
    tools=[tavily_search_tool],
    prompt="You are a GRC analyst that is the subject matter expert for ISO27001. You must return information that is up-to-date."
    )

# HumanMessage is just a way of saying "this was passed by a human"
messages = [HumanMessage(content="Tell me about password policies")]
messages = agent.invoke({"messages": messages})
for m in messages['messages']:
    m.pretty_print()