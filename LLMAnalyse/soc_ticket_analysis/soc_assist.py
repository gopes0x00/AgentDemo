import sys
import os
import sqlite3
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, END, MessagesState
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from pydantic.v1 import BaseModel, Field
from elasticsearch8 import Elasticsearch

load_dotenv()
if not os.environ.get("ANTHROPIC_API_KEY"):
    print("environment variable ANTHROPIC_API_KEY not set")
    sys.exit(1)

ES_API_KEY = os.environ.get("ES_API_KEY", None)
ES_USER = os.environ.get("ES_USER", None)
ES_PASSWORD = os.environ.get("ES_PASSWORD", None)

# Custom state for agent
class MultiAgentState(MessagesState):
    question: HumanMessage
    question_type: str
    answer: str


question_category_prompt = '''You are an information security incident manager. Your task is to classify the incoming questions.
Depending on your answer, question will be routed to the right team, so your task is crucial for our team.
There are 3 possible question types:
- LOGS - questions related to logs stored in Elastic
- AWS - questions related to AWS configuration
- CODE - questions related to code analysis

This is IMPORTANT, you should only ever return LOGS, GRC, or CODE. Add no additional context on your decision.
If you think all questions are answered then do not call another node and end.
'''


def router_node(state: MultiAgentState):
    messages = [
        SystemMessage(content=question_category_prompt),
        HumanMessage(content=state['question'])
    ]
    model = ChatAnthropic(model="claude-3-5-sonnet-latest")
    response = model.invoke(messages)
    return {"question_type": response.content}


def elastic_audit_lookup(messagedata: str):
    """
    Takes a keyword to search the audit logs for
    """
    try:
        hosts = [{"host": "127.0.0.1", "port": int("9200"), "scheme": "https"}]
        es = Elasticsearch(
            hosts,
            api_key=ES_API_KEY,
            verify_certs=False,
            headers={
                "Accept": "application/vnd.elasticsearch+json;compatible-with=8",
                "Content-Type": "application/vnd.elasticsearch+json;compatible-with=8"
            })
    
        es_query = {"bool": {"filter": []}}
        es_query["bool"]["filter"].append({"match": {"messages.data": messagedata}})
        time_range = {"range": {"@timestamp": {}}}
        time_range["range"]["@timestamp"]["gte"] = "now-7d"
        time_range["range"]["@timestamp"]["lte"] = "now"
        es_query["bool"]["filter"].append(time_range)

        if not es_query["bool"]["filter"]:
            es_query = {"match_all": {}}

        response = es.search(
            index="go-audit*",
            body={
                "query": es_query,
                "size": 50,
                "_source": ["messages.data", "@timestamp"],
                "sort": [{"@timestamp": {"order": "desc"}}]
            }
        )

        return(response)
        
    except Exception as e:
        return (f"Failed to initialize Elasticsearch client: {str(e)}")


def elastic_ioc_lookup(ioc):
    "Searches all indices and fields for a specific indicator of compromise"
    try:
        hosts = [{"host": "127.0.0.1", "port": 9200, "scheme": "https"}]
        es = Elasticsearch(
            hosts,
            api_key=ES_API_KEY,
            verify_certs=False,
            headers={
                "Accept": "application/vnd.elasticsearch+json;compatible-with=8",
                "Content-Type": "application/vnd.elasticsearch+json;compatible-with=8"
            }
        )

        es_query = {
            "bool": {
                "must": [
                    {
                        "query_string": {
                            "query": f"\"{ioc}\"",
                            "fields": ["*"]
                        }
                    }
                ],
                "filter": [
                    {
                        "range": {
                            "@timestamp": {
                                "gte": "now-7d",
                                "lte": "now"
                            }
                        }
                    }
                ]
            }
        }

        response = es.search(
            index="_all",
            body={
                "query": es_query,
                "size": 50,
                "_source": ["message", "messages.data", "@timestamp"],
                "sort": [{"@timestamp": {"order": "desc"}}]
            }
        )

        return (response)

    except Exception as e:
        return f"Failed to initialize Elasticsearch client: {str(e)}"


class ElasticQuery(BaseModel):
    query: str = Field(description="Elastic query to run")


@tool(args_schema=ElasticQuery)
def execute_elastic_audit_query(query: str) -> str:
    """Takes a string and searches for the term within messages.data field in audit log events.
    """
    return elastic_audit_lookup(query)


@tool(args_schema=ElasticQuery)
def execute_elastic_ioc_query(query: str) -> str:
    """Runs a search across all elastic logs for specific IOC. The IOC must be a single string"""
    return elastic_ioc_lookup(query)


elastic_expert_system_prompt = '''You are an expert SOC analyst and are proficient at using
Elastic to search data and understand security alerts and incidents.

You have two tools at your disposal:
1. execute_elastic_ioc_query - this accepts a single string for IOC, e.g. an IP address, a hash, a filename and runs a search across all logs
2. execute_elastic_query - this accepts a single string term.

Your input will be a SOC alert raised by the SIEM. Use your expertise to pick the correct tool for the job. When giving your recommendations 
keep in mind that the environment is hosted in AWS. 
'''


def elastic_expert_node(state: MultiAgentState):
    model = ChatAnthropic(model="claude-3-5-sonnet-latest")
    elastic_agent = create_react_agent(model,
                                       [execute_elastic_audit_query,
                                           execute_elastic_ioc_query],
                                       checkpointer=memory,
                                       state_modifier=elastic_expert_system_prompt)
    messages = [HumanMessage(content=state['question'])]
    result = elastic_agent.invoke({"messages": messages})
    return result


aws_expert_system_prompt = '''You are a cloud security expert with a focus on AWS'''


def aws_expert_node(state: MultiAgentState):
    model = ChatAnthropic(model="claude-3-5-sonnet-latest")
    messages = [HumanMessage(content=state['question'])]
    result = model.invoke(messages)
    return {"answer": result.content}


code_analysis_expert_system_prompt = '''You are an appsec expert and will be called on to analyse code'''


def code_analysis_expert_node(state: MultiAgentState):
    model = ChatAnthropic(model="claude-3-5-sonnet-latest")
    messages = [HumanMessage(content=state['question'])]
    result = model.invoke(messages)
    return {"answer": result.content}


def route_question(state: MultiAgentState):
    return state['question_type']


# Create the SQLite saver correctly
conn = sqlite3.connect(':memory:', check_same_thread=False)
memory = SqliteSaver(conn)

# Build the graph
builder = StateGraph(MultiAgentState)
builder.add_node("router", router_node)
builder.add_node('elastic_expert', elastic_expert_node)
builder.add_node('code_expert', code_analysis_expert_node)
builder.add_node('aws_expert', aws_expert_node)
builder.add_conditional_edges(
    "router",
    route_question,
    {'LOGS': 'elastic_expert',
     'CODE': 'code_expert',
     'AWS': 'aws_expert'}
)

builder.set_entry_point("router")
builder.add_edge('elastic_expert', END)
builder.add_edge('code_expert', END)
builder.add_edge('aws_expert', END)
graph = builder.compile(checkpointer=memory)

# Test with different questions
# Threads are used to separate conversations
soc_ticket = """
Suspicious use of whoami from IP address 18.171.55.110

1. Investigate IOC 18.171.55.110
2. Investigate audit logs for suspicious activity on affected host
"""


thread = {"configurable": {"thread_id": "1"}}
results = []

for s in graph.stream({'question': soc_ticket,}, thread, stream_mode="updates"):
    try:
        for m in s["elastic_expert"]["messages"]:
            m.pretty_print()
    except:
        print(s)
    results.append(s)


thread = {"configurable": {"thread_id": "2"}}
question = '''Analyse the following code
class VulnerableHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Parse the URL and query parameters
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Basic routing
        if parsed_url.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            
            # Simple form for demonstration
            self.wfile.write(b"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Command Execution Demo</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                    h1 { color: #333; }
                    .form-container { background: #f9f9f9; padding: 20px; border-radius: 5px; max-width: 600px; }
                    input[type=text] { width: 80%; padding: 8px; margin: 10px 0; }
                    input[type=submit] { background: #4CAF50; color: white; padding: 10px 15px; border: none; cursor: pointer; }
                    pre { background: #f0f0f0; padding: 15px; border-left: 4px solid #ccc; overflow: auto; }
                    .warning { color: red; font-weight: bold; }
                </style>
            </head>
            <body>
                <h1>Command Execution Demo</h1>
                <div class="warning">WARNING: This server is vulnerable to command injection!</div>
                <p>This is a demonstration of an insecure application for educational purposes.</p>
                
                <div class="form-container">
                    <h2>Ping a host</h2>
                    <form action="/ping" method="get">
                        <label for="host">Host to ping:</label><br>
                        <input type="text" id="host" name="host" value="127.0.0.1"><br>
                        <input type="submit" value="Ping Host">
                    </form>
                </div>
            </body>
            </html>
            """)
            
        elif parsed_url.path == "/ping":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            
            # VULNERABLE CODE - Command injection vulnerability!
            # This deliberately allows command injection through the 'host' parameter
            if "host" in query_params:
                host = query_params["host"][0]
                
                # INTENTIONALLY VULNERABLE - DO NOT USE IN PRODUCTION
                # The vulnerability is that we directly use user input in a shell command
                try:
                    # DELIBERATELY INSECURE - This allows command injection
                    command = f"ping -c 1 {host}"
                    logging.info(f"Executing command: {command}")
                    output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
                    
                    response = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Ping Results</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                            h1 {{ color: #333; }}
                            pre {{ background: #f0f0f0; padding: 15px; border-left: 4px solid #ccc; overflow: auto; }}
                            .warning {{ color: red; font-weight: bold; }}
                        </style>
                    </head>
                    <body>
                        <h1>Ping Results</h1>
                        <div class="warning">WARNING: This server is vulnerable to command injection!</div>
                        <p>Executed command: {command}</p>
                        <pre>{output.decode('utf-8', errors='replace')}</pre>
                        <p><a href="/">Back to home</a></p>
                    </body>
                    </html>
                    """
                    self.wfile.write(response.encode())
                except subprocess.CalledProcessError as e:
                    error_message = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Error</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                            h1 {{ color: #333; }}
                            pre {{ background: #f0f0f0; padding: 15px; border-left: 4px solid #ccc; overflow: auto; }}
                            .error {{ color: red; }}
                        </style>
                    </head>
                    <body>
                        <h1 class="error">Error Executing Command</h1>
                        <p>The command failed with exit code: {e.returncode}</p>
                        <pre>{e.output.decode('utf-8', errors='replace')}</pre>
                        <p><a href="/">Back to home</a></p>
                    </body>
                    </html>
                    """
                    self.wfile.write(error_message.encode())
            else:
                self.wfile.write(b"No host specified")
        else:
            self.send_error(404, "Page not found")
    
    def log_message(self, format, *args):
        logging.info("%s - %s", self.client_address[0], format % args)
'''
results = []
for s in graph.stream({
  'question': question,
}, thread):
  print(s)
  results.append(s)
print(results[-1]["code_expert"]["answer"])



thread = {"configurable": {"thread_id": "3"}}
question = "How can I block a malicious IP address from accessing my web server hosted in EC2?"
results = []
results = []
for s in graph.stream({
  'question': question,
}, thread):
  print(s)
  results.append(s)
print(results[-1]["aws_expert"]["answer"])