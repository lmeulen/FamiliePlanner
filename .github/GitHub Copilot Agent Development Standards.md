# GitHub Copilot Agent Development Standards

This document serves as the authoritative guide for GitHub Copilot's operations within this repository. It defines the technical architecture, 
development workflows, and professional standards required to maintain a high-quality codebase.

## Architectural Flexibility and Technical Stack

The GitHub Copilot Agent is empowered to select the most appropriate application architecture based on user requirements. This includes:

-   **Standalone Webpage:** For static content, portfolios, simple informational sites or sites with restricted logic, e.g. simple parsing of Excel documents can be performed in a standalone webpage.
-   **Client/Server Application:** For interactive web applications requiring backend logic, data persistence, and user authentication.
-   **Command-Line Interface (CLI) Application:** For scripting, automation, or tools that do not require a graphical user interface.

Regardless of the chosen architecture, the following technical stack and principles apply:


When applicable, the chosen architecture will utilize a decoupled approach, separating the presentation layer from the server-side logic. The following 
table outlines the primary technologies and their respective roles across different application types:

| Layer | Technology | Key Responsibilities |
| :--- | :--- | :--- |
| **Frontend** | HTML, JavaScript, TypeScript | User interface, client-side logic, and type-safe component development. |
| **Backend** | Python, Flask, SQLite, Pydantic | Server-side API development, business logic, and database orchestration. |
| **Intelligence** | ChatNS (LLM), chatbot.py wrapper | Text completions, code analysis, and semantic search integration. |

### Cross-Origin Resource Sharing (CORS) Mitigation

When developing web applications, particularly those interacting with external APIs, potential Cross-Origin Resource Sharing (CORS) issues must be 
anticipated. All front-end only webapplication projects should be designed to facilitate the use of a local proxy during development to circumvent CORS restrictions. 
This ensures a smooth development workflow and prevents common integration challenges.

### LLM Integration with ChatNS

All Large Language Model (LLM) operations must be routed through the **ChatNS** interface. This integration supports two primary modalities:
1.  **Completions:** Utilized for generating structured text, refactoring code, and providing contextual explanations. This is OpenAI API compatible, 
except the location of the API key in the header (see code examples below)
2.  **Semantic Search:** Employed for advanced information retrieval, allowing the agent to locate relevant project context based on conceptual  meaning rather than literal keyword matching.

For complex application using PYthon, a chatbot.py wrapper is available that wraps all complex functionality to ease the use. Detailed information can be found below. Only use this when required due to complexity.


## Python Development and Environment Management

To ensure reproducibility and security, all Python development must adhere to strict environment and configuration standards.

> "A well-managed environment is the foundation of a stable deployment. Virtual environments prevent dependency conflicts, while externalized 
configuration protects sensitive credentials." 

### Environment Isolation

All Python projects must utilize a dedicated virtual environment stored in the `.venv/` directory. This directory must remain local and should 
never be committed to version control. Furthermore, the `requirements.txt` file must be updated immediately upon the installation of any new 
package to ensure the environment can be replicated across different systems.

### Configuration and Security

Sensitive configuration data, including API keys and database credentials, must be stored in a `.env` file at the project root. The `python-dotenv` 
library is the mandatory tool for loading these variables into the Flask application. Hardcoding credentials within the source code is strictly 
prohibited to prevent accidental exposure of secrets.

## Documentation and Workflow Integrity

Maintaining clear and up-to-date documentation is a core requirement for all development activities.

### Continuous Documentation

The `README.md` file serves as the primary entry point for the repository. It must be kept current with every significant change, including new 
feature additions, modifications to the build process, or updates to the dependency list. Documentation should be written in a clear, 
professional style that facilitates onboarding for other developers or AI agents.

### Professional Commit Standards

Git commit messages must follow the imperative mood and provide a concise summary of the changes (e.g., "Implement semantic search endpoint"). 
Large changes should be broken down into smaller, logical commits to facilitate easier code reviews and debugging.

## Recommended Professional Enhancements

Beyond the core requirements, the following practices are recommended to elevate the project's reliability and maintainability.

### Automated Testing and Validation

Reliability is ensured through rigorous testing. Every new feature or significant refactor should be accompanied by automated tests. For the 
Python backend, **pytest** is the preferred framework. Running the full test suite is a prerequisite for finalizing any pull request or commit.

### Robust Error Handling and Logging

Applications must be resilient to failure. Implement comprehensive error handling in Flask using structured `try-except` blocks and appropriate 
HTTP status codes. For tracking application state and debugging, utilize Python's built-in `logging` module rather than standard output statements.

### API Specification and Documentation

As the API grows, maintaining a clear specification becomes critical. Every Flask route should include a Docstring detailing its purpose, 
expected parameters, and potential error responses. For complex systems, adopting the **OpenAPI (Swagger)** specification is highly encouraged 
to provide interactive documentation.

## Example code snippets

### Example Python code for finding available models:
```
url = 'https://gateway.apiportal.ns.nl/genai/v1/chat/completions'    
prompt = "Wat is de hoofdstad van Frankrijk?"
headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0',
        'Ocp-Apim-Subscription-Key': API_KEY
    }
payload = {
    "messages": [
        {
            "role": "user",
            "content": prompt
        }
    ],
    "model": MODEL
}   
response = requests.post(url, headers=headers, json=payload)
answer = response.json()['choices'][0]['message']['content']
```

### Example Python code for finding available models:
```
MODELS_URL = "https://gateway.apiportal.ns.nl/genai/v1/models"
headers = {
    "Accept": "application/json",
    "Ocp-Apim-Subscription-Key": api_key,
}
response = requests.get(MODELS_URL, headers=headers, timeout=30)
payload = response.json()
models = payload.get("data")
for index, model in enumerate(models, start=1):
    print(f"{index:2.0f}. {model.get('id')}")
```

### Example Python code for semantic search

```
url = 'https://gateway.apiportal.ns.nl/genai/v1/semantic_search'
payload = {
    "prompt": query,
    "top_n": top_n,
    "bucket_id": bucket_id,
    "min_cosine_similarity": 0.75
}
response = requests.post(url, headers=headers, json=payload)
result = response.json()
```

### Example implementation of a proxy server 

```
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, os, json
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("CHATNS_KEY")

app = Flask(__name__)
CORS(app)  # Allow all origins

DEFAULT_CHAT_URL = "https://gateway.apiportal.ns.nl/genai/v1/chat/completions"
DEFAULT_SEMANTIC_SEARCH_URL = "https://gateway.apiportal.ns.nl/genai/v1/semantic_search"
DEFAULT_API_KEY = API_KEY
DEFAULT_MODEL = "gpt-4.1-mini"

@app.route("/api/chatns", methods=["POST"])
def relay():
    data = request.get_json(force=True) or {}
    target_url = data.get("targetUrl") or DEFAULT_CHAT_URL
    method = (data.get("method") or "POST").upper()
    payload = data.get("payload")

    if payload is None and method in {"POST", "PUT", "PATCH"}:
        payload = {
            "messages": [{"role": "user", "content": data.get("prompt", "")}],
            "model": data.get("model", DEFAULT_MODEL)
        }

    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": data.get("apiKey") or DEFAULT_API_KEY,
        "User-Agent": "PlaybookEditor/1.0"
    }
    try:
        request_kwargs = {
            "headers": headers,
            "timeout": 60
        }

        if method in {"POST", "PUT", "PATCH"}:
            request_kwargs["json"] = payload
        elif payload:
            request_kwargs["params"] = payload

        resp = requests.request(method, target_url, **request_kwargs)
        return (resp.text, resp.status_code, {"Content-Type": "application/json"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/semantic_search", methods=["POST"])
def semantic_search_relay():
    data = request.get_json(force=True) or {}
    target_url = data.get("targetUrl") or DEFAULT_SEMANTIC_SEARCH_URL
    
    # Extract semantic search parameters
    payload = data.get("payload") or {
        "prompt": data.get("prompt", data.get("query", "")),
        "top_n": data.get("top_n", 5),
        "bucket_id": data.get("bucket_id", ""),
        "min_cosine_similarity": data.get("min_cosine_similarity", 0.75)
    }

    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": data.get("apiKey") or DEFAULT_API_KEY,
        "User-Agent": "PlaybookEditor/1.0"
    }

    try:
        resp = requests.post(target_url, headers=headers, json=payload, timeout=60)
        return (resp.text, resp.status_code, {"Content-Type": "application/json"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=7071, debug=True)
```

## chatbot.py documentation
Below is a concise but complete guide for an AI agent (or developer) to understand and use this codebase to its full potential. It explains how the main classes and helper functions work, what the HTTP/JSON contracts look like, how tools and MCP servers are exposed to the LLM, how to ingest documents (RAG flow), how to call completions and embeddings, and typical usage patterns with short code examples.

Table of Contents
- Quick summary
- Key helper functions
  - check_parameter
  - truncate_json
  - extract_text_from_file
- Tool system
  - ToolManager overview
  - Local tools: registration and schema generation
  - MCP servers (fastmcp) and remote tools
  - How tool-calls are processed (tool_calls loop)
  - How the LLM receives tool schemas (payload)
- Chatbot (ChatNS) API
  - Initialization and headers / authentication
  - Model, temperature, system prompt, and costs
  - Calling the LLM (completions)
  - prompt() vs prompt_rag()
  - Embeddings
- Buckets, Sources, Items (RAG storage API)
  - Endpoints and payloads
  - Hashing items
  - Add / update / delete items
  - Listing/searching items
  - find_* helpers
- High-level wrappers
  - BucketChat
  - BucketManager
  - SourceManager
- Error handling and limitations
- Minimal usage recipes (examples)

---

Quick summary
- This code provides a Chatbot client (ChatNS) that talks to NS GenAI gateway endpoints for chat completions, semantic search, embeddings, and bucket/source/item management.
- It also supports registering "tools": local Python functions (ToolManager) and remote MCP tools (fastmcp Client). When tools are enabled, they are added to the LLM request schema so the model can call them. The Chatbot implements the tool-call loop: if the LLM returns tool_calls, the code executes them and feeds results back into the conversation.
- The library includes helpers to ingest documents from many file formats into text (extract_text_from_file) so they can be added to buckets as items for RAG.

Key helper functions

1) check_parameter(name, value, expected_type, min_value=None, max_value=None, not_none=False)
- Validates input parameters used through the library.
- Raises TypeError if the value is not instance of expected_type.
- For numeric types, optionally checks min_value and max_value.
- For strings, if not_none=True it rejects empty string.
- Important: many public methods call this for input validation. Use correct types and ranges.

2) truncate_json(json_obj, max_length=10)
- Utility used for logging payloads: truncates keys and long string values to max_length and appends "..." if truncated.
- Works recursively for dicts and lists.

3) extract_text_from_file(source)
- Accepts either a URL (http/https) or a local path.
- Supported extensions: .pdf, .docx, .txt, .html/.htm, .md, .pptx, .xlsx, .msg
- Downloads (requests.get) when URL, or opens local file.
- Returns a text string extracted from the document or "" if unsupported or failure.
- Useful for pre-processing documents before adding them as items to a source in a bucket.

Supported extraction functions:
- PDF: PyPDF2.PdfReader pages' extract_text()
- DOCX: python-docx Document paragraphs
- TXT/MD: read bytes decode 'utf-8'
- HTML: BeautifulSoup get_text(separator='\n')
- PPTX: python-pptx slides shapes text
- XLSX: openpyxl iter_rows values_only
- MSG: extract_msg.Message fields (sender, to, cc, subject, date, body)

Tool system

ToolManager (used internally by Chatbot.tools)
- Keeps:
  - _local_tools: mapping name -> callable
  - _mcp_servers_info: mapping server_url -> {"client": fastmcp.Client, "tools": {...}}
  - _mcp_tool2server: mapping tool_name -> server_url
  - _tools_schema: cached OpenAI/LLM tool schema list
  - _schema_valid: boolean cache flag

Local tools
- Add with ToolManager.add_tool(func) or Chatbot.add_tool(func).
- The library uses inspect.signature and docstring_parser to generate an OpenAI-like function schema for each local tool in get_tools_schema():
  - Parameter types inferred: int -> integer, float -> number, bool -> boolean, default -> string
  - The docstring param description (if present) is used for parameter descriptions.
  - All defined function parameters are marked as required in the generated schema (required_params list).
- The generated tool schema is used in LLM payload when tools_enabled is True.

MCP (fastmcp) remote tools
- Add an MCP server via ToolManager.add_mcp_server(server_url) or Chatbot.add_mcp_server(server_url).
- This creates a fastmcp.Client(server_url), lists tools via client.list_tools() and stores them into _mcp_servers_info.
- For each MCP tool, _mcp_tool2server[tool.name] = server_url.
- get_tools_schema includes MCP tools converted to the function schema via their tool.inputSchema (the remote tool's declared input schema).
- execute_mcp_tool(tool_name, **kwargs):
  - Finds corresponding fastmcp.Client and calls client.call_tool(tool_name, args) inside an async wrapper using asyncio.run.
  - The code expects result.content[0].text (so remote responses must follow this shape) and returns that string.

Tool call processing
- LLM side: The Chatbot.__call_llm() posts a payload with messages, temperature, model, and when tools_enabled: payload["tools"] = tools schema and payload["tool_choice"]="auto".
- When receiving a response, Chatbot.prompt() checks response['choices'][0]['message'] for a key "tool_calls".
- Expected format of each tool_call: dictionary with keys like "id" and "function": {"name": <tool_name>, "arguments": "<json-string>"}.
- process_tool_calls(tool_calls) iterates tool_calls:
  - loads arguments JSON,
  - if tool_name is local -> execute_local_tool(tool_name, **arguments)
  - if tool_name maps to an MCP server -> execute_mcp_tool(tool_name, **arguments)
  - returns list of {"id": call_id, "output": output}
- After executing tool calls, Chatbot.prompt constructs tool messages:
  - {"role": "tool", "tool_call_id": result["id"], "content": str(result["output"])}
  - It appends the original message (with tool_calls) and these tool messages to self.messages, then re-calls the LLM (loop) until no tool_calls are returned.
- Note: The tool_call contract is LLM-specific. The code expects the LLM to return "tool_calls" with JSON-stringified arguments.

Chatbot (ChatNS) API

Initialization
- chatbot = Chatbot(apikey, systemprompt=None, temperature=0.7, deployment_id='gpt_4')
- Auth: apikey is placed in header 'Ocp-Apim-Subscription-Key': apikey. The client sets headers with Content-Type: application/json, User-Agent: Mozilla/5.0.
- Messages list initially contains a system message equal to systemprompt if provided.

Model selection
- set_model(deployment_id: str)
  - Validates input and matches against a list of allowed deployment IDs (the code includes a final list).
  - If invalid id -> raises ValueError.

System prompt & temperature
- set_systemprompt(systemprompt: str) updates system message (replaces first message) or creates it.
- set_temperature(temperature: float) enforces 0.0 <= temperature <= 2.0.

Calling the LLM (completions)
- __call_llm() sends POST to: https://gateway.apiportal.ns.nl/genai/v1/chat/completions
  - payload: {"messages": self.messages, "temperature": self.temperature, "model": self.deployment_id}
  - if tools_enabled: adds "tools": tools_schema and "tool_choice": "auto"
- Response handling:
  - The raw JSON response is returned by __call_llm() and appended to costs lists using response['usage'].
  - Chatbot.prompt handles the tool_calls loop and ultimately appends final assistant content to self.messages and returns:
    - By default: the assistant text string (answer)
    - If detailed_result=True: returns the full LLM response JSON

Costs
- The client stores usage info per call in self.costs and total_costs
- get_costs() aggregates completion_tokens and prompt_tokens from self.costs into a dict.

prompt() vs prompt_rag()
- prompt(prompt_text, detailed_result=False):
  - Adds a user message then calls the LLM; handles tool_calls loop mentioned above.
  - Returns assistant answer string or full JSON if detailed_result True.
- prompt_rag(query, bucket_id, top_n=5, keep_context=True):
  - First runs search_in_bucket(query, bucket_id, top_n) to retrieve context documents (semantic search).
  - Aggregates items' 'content' into one "context" string and uses add_context(context) which appends a system message with the context.
  - Then calls prompt(query).
  - If keep_context is False, removes messages with role 'context' (note: in code add_context uses role "system", but prompt_rag attempts to remove messages with role == 'context' — small mismatch to be aware of).
  - Returns answer or full JSON if detailed_result True.

Embeddings
- create_embedding(text: str, dimensions: int=1024)
  - Posts to: https://gateway.apiportal.ns.nl/genai/v1/embeddings
  - payload: {"model": "text_embedding_3_large", "dimensions": dimensions, "input": text}
  - Returns response.json()['data'][0]['embedding'] (list of floats)
  - Useful to compute and store vectors externally if you want to do your own semantic index.

Buckets, Sources, Items (RAG storage API)

Base headers and endpoints
- All bucket/source/item operations hit gateway.apiportal.ns.nl/genai/v1 with the Ocp-Apim-Subscription-Key header as API key.

Create source
- create_source(bucket_id:int, source_name:str) -> external_source_id (int)
  - POST https://gateway.apiportal.ns.nl/genai/v1/buckets/{bucket_id}/external_sources
  - payload: {'external_source_name': source_name}
  - Response JSON expected to contain "external_source_id"

List/get source(s)
- get_sources(bucket_id) -> list
  - GET https://.../buckets/{bucket_id}/external_sources
- get_source(bucket_id, source_id) -> dict
  - GET https://.../buckets/{bucket_id}/external_sources/{source_id}

Rename / Delete source
- rename_source -> PATCH same URL with payload {'external_source_name': new_name}
- delete_source -> DELETE same URL

Items
- add_item(bucket_id, source_id, content, item_url)
  - POST https://.../buckets/{bucket_id}/external_sources/{source_id}/items
  - payload: {'url': item_url, 'content': content, 'content_hash': self.hash(content)}
  - Response should include "external_item_id"
- get_items(bucket_id, source_id) -> list (GET)
- get_item(bucket_id, source_id, item_id) -> dict (GET)
- get_item_by_url(bucket_id, source_id, item_url) -> dict (scans items by 'url')
- find_item_id_for_item_url -> scans items and returns external_item_id
- update_item_by_id(bucket_id, source_id, item_id, content, content_url)
  - PATCH https://.../items/{item_id}
  - payload: {'url': content_url, 'content': content, 'content_hash': self.hash(content)}
  - Note: doc comment "TODO: Fix this, update should really update item instead of deleting and adding" — but it uses PATCH, expect server to accept partial update.
- update_item_by_url finds the item_id then calls update_item_by_id.
- add_or_update_item: if item with URL exists -> update; else -> add.

Hashing
- hash(content) -> sha256 hex digest used as content_hash in item payloads. Use this to detect duplicates or ensure content integrity.

Search (semantic_search)
- search_in_bucket(query, bucketid, top_n=5)
  - POST https://gateway.apiportal.ns.nl/genai/v1/semantic_search
  - payload: {"prompt": query, "top_n": top_n, "bucket_id": bucketid, "min_cosine_similarity": 0.75}
  - Returns JSON (expected to be list/dict with items that include 'content' for prompt_rag). The exact response schema is defined by the gateway, but prompt_rag expects list-like results where each item has 'content'.

High-level wrappers

BucketChat
- Lightweight wrapper that stores a bucket_id and contains a Chatbot instance.
- Methods:
  - search_in_bucket(query, top_n) – calls chatbot.search_in_bucket(bucket_id)
  - prompt(query, top_n=5, rag=True, keep_context=True) – if rag True uses prompt_rag(bucket_id)
  - new_chat() -> resets chat
- Use BucketChat when you work primarily with a single bucket and want simplified calls.

BucketManager and SourceManager
- Higher-level classes that call Chatbot methods with self.bucket_id.
- BucketManager provides create_source, rename_source, get_sources, find_source_id_for_source_name, delete_source, get_source_manager(source_id) -> SourceManager
- SourceManager provides add_item/update/delete/get functions for a specific source id and bucket id.
- Also provide print helpers for listing.

Error handling and limitations / gotchas
- Authentication: API key must be valid and placed in 'Ocp-Apim-Subscription-Key' header.
- Some endpoints expect certain keys in the server responses (e.g., external_source_id, external_item_id). If the gateway returns different keys the code will raise.
- prompt_rag: after adding context the code uses add_context which adds a "system" role message. Later prompt_rag tries to remove messages with role == 'context' if keep_context False — mismatch; to remove the system-added context you'd need to remove role == 'system' messages carefully or adjust code.
- Tools: local function parameter types are inferred from annotations. If you use complex types (dict, list, custom objects), the schema will mark them as string by default — adapt your docstrings or wrap arguments as simple primitive types or JSON strings.
- MCP tools: fastmcp Client must function in your environment and remote tools must provide input schema compatible with conversion logic. Remote execution uses asyncio.run to drive async calls.
- add_or_update_item and update_item_by_id rely on the gateway implementing PATCH semantics correctly.
- create_embedding uses model "text_embedding_3_large" and dimensions parameter must be within 1..3072 by check_parameter.

Minimal usage recipes

1) Basic chat:
```python
from this_module import Chatbot

cb = Chatbot(apikey="MY_API_KEY", systemprompt="You are an assistant for NS internal docs.")
cb.new_chat()
answer = cb.prompt("What are the opening hours of the NS service desk?")
print(answer)
```

2) Register a local tool and enable tools:
```python
def my_add(x: int, y: int) -> int:
    """Add two integers.
    Args:
      x: first integer
      y: second integer
    """
    return x + y

cb.add_tool(my_add)
cb.enable_tools(True)
response = cb.prompt("Please compute 3 + 5 and use the tool if needed.")
print(response)
```
- The function signature and docstring will be parsed into a tool schema. The LLM may call it via tool_calls and the client will execute it.

3) Add MCP server and call its tools:
```python
cb.add_mcp_server("http://mcp-server.example.com:1234")
# After add_mcp_server, remote tools are discoverable.
cb.enable_tools(True)
resp = cb.prompt("Use the remote tool 'weather_forecast' for Amsterdam.")
print(resp)
```
- The MCP client lists remote tools when adding the server. execute_mcp_tool uses fastmcp.Client.call_tool.

4) Ingest documents into a bucket and ask RAG queries
Steps:
- Create or find source in your bucket.
- Extract text from local file or URL with extract_text_from_file.
- Add items to the source with unique content URLs (the item_url is an identifier — could be a document path or a generated uuid).
- Ask prompt with rag=True.

Example:
```python
from this_module import BucketChat, extract_text_from_file

bucket_id = 42
apikey = "MY_API_KEY"
bc = BucketChat(apikey, bucket_id, systemprompt="You are NS knowledge base assistant.")
bc.new_chat()

# 1) Create source (if not existing)
source_name = "HR-policies"
src_id = bc.get_bucketmanager().find_source_id_for_source_name(source_name)
if src_id is None:
    src_id = bc.get_bucketmanager().create_source(source_name)

# 2) Extract text and add
text = extract_text_from_file("/path/to/employee_handbook.pdf")
unique_url = "employee_handbook_v1"  # could be a uuid or file URL
sm = bc.get_bucketmanager().get_source_manager(src_id)
sm.add_or_update_item(text, unique_url)

# 3) Ask RAG question
answer = bc.prompt("What is the parental leave policy for part-time employees?", rag=True)
print(answer)
```

5) Compute embeddings (for external index):
```python
embedding = cb.create_embedding("This is a text to embed.", dimensions=1024)
# store embedding in your vector DB with metadata: bucket/source/item id
```

Inspecting tools schema (for debugging)
```python
cb.tools.add_tool(my_add)
schema = cb.tools.get_tools_schema()  # builds and saves tools_schema.json
print(schema)
```
- This writes tools_schema.json to disk so you can inspect the OpenAI-like function schemas.

Process tool_calls: how LLM and agent interact
- The LLM can return a message containing tool_calls: list of call specs.
- Each call contains a function info with name and arguments as JSON string.
- process_tool_calls parses args and routes call to local or remote tools.
- The produced output(s) are appended as role "tool" messages with tool_call_id to the conversation.
- The next call to the LLM will include the tool results so the model can continue reasoning.

Useful implementation notes / suggestions
- When adding local tools, annotate parameters with basic types (int, float, bool, str) and provide docstrings with parameter descriptions so schema generation is high-quality.
- Use unique item_url values when adding items so find_item_id_for_item_url works reliably.
- Consider storing embeddings (create_embedding) separately in your preferred vector DB if you plan custom search pipelines.
- If you rely on MCP servers, validate that the remote tool output shape matches the expectations (result.content[0].text or result.data). The code currently expects result.content[0].text.
- Because prompt_rag constructs a single concatenated context string from search results, consider truncating/summarizing long documents before adding them to context to avoid token limits.

Summary of main endpoints used by the library
- Chat completions: POST /genai/v1/chat/completions (payload: messages, model, temperature, plus optional tools/tool_choice)
- Embeddings: POST /genai/v1/embeddings (payload: model, dimensions, input)
- Semantic search: POST /genai/v1/semantic_search (payload: prompt, top_n, bucket_id, min_cosine_similarity)
- Buckets/Sources/Items:
  - POST /buckets/{bucket_id}/external_sources
  - GET /buckets/{bucket_id}/external_sources
  - PATCH/DELETE /buckets/{bucket_id}/external_sources/{source_id}
  - POST /buckets/{bucket_id}/external_sources/{source_id}/items
  - GET/PATCH/DELETE /buckets/{bucket_id}/external_sources/{source_id}/items/{item_id}
  - GET /buckets/{bucket_id}/external_sources/{source_id}/items

If you want, I can:
- Provide a runnable example script that ingests a set of documents from disk and indexes them into a bucket (using extract_text_from_file -> add_item).
- Show a detailed example of creating a local tool and a mock LLM response including tool_calls and how the agent processes it.
- Explain how to adapt tool schema generation for optional vs required parameters (the current code marks all parameters as required).