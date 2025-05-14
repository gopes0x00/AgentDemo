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

load_dotenv()

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("environment variable ANTHROPIC_API_KEY not set")
    sys.exit(1)

async def main():
    model = ChatAnthropic(model="claude-3-5-sonnet-latest")

    server_params = StdioServerParameters(
        command="python",
        args=["mcp_math.py"]
    )

    messages = [HumanMessage(content="Hi George")]


    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await load_mcp_tools(session)

            agent = create_react_agent(model, tools)
            messages = await agent.ainvoke({"messages": messages})
            for m in messages['messages']:
                m.pretty_print()

if __name__ == "__main__":
    asyncio.run(main())