import os
from elasticsearch8 import Elasticsearch
from elasticsearch8.exceptions import ConnectionError, AuthenticationException
from typing import Dict, List, Any
from dotenv import load_dotenv

load_dotenv()
ES_API_KEY = os.environ.get("ES_API_KEY")
ES_USER = os.environ.get("ES_USER")
ES_PASSWORD = os.environ.get("ES_PASSWORD")

def search_audit_logs(messagedata):

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
        es_query["bool"]["filter"].append(messagedata)
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

        print(response)
        
    except Exception as e:
        return (f"Failed to initialize Elasticsearch client: {str(e)}")

if __name__ == "__main__":
    s = search_audit_logs("cp")
    print(s)