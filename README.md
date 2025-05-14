## Prerequisites

1. Anthropic API key (note this is not the same as a claude subscription)
2. Tavily API key (free)
3. Create a .env file in both `react_agents` and `soc_ticket_analysis.py` with the following
```
TAVILY_API_KEY=<tavily_api_key>
ANTHROPIC_API_KEY=<anthropic_api_key>
```

## Terraform
The terraform code is just used to spin up a couple of servers for the attack scenario.

## soc_assist.py
For this to work you will need a local version of elastic running (see `run_elastic.sh`) and you'll need to import the various files found in server_logs.zip

To upload files see:
https://www.elastic.co/docs/manage-data/ingest/upload-data-files

When you import the data you need to set the time field otherwise the import won't work. For JSON this is easy
but for the others you need to give it a time format and it should autofind the time field.

## Local LLM
If you have a laptop powerful enough you can also run local models using (ollama)[https://ollama.com/], I found the models weren't as effective as claude or gpt4o