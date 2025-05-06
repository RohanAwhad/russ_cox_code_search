## hackhub API Protocol Documentation

This document outlines the protocol for interacting with the code search service.

### Starting the Service

```bash
uvx /Users/rohan/1_Porn/russ_cox_code_search/master/main.py /path/to/your/project
```

The server will index your project and begin watching for file changes.

### Communication Protocol

The API uses a simple JSON-based protocol with Content-Length headers, similar to the Language Server Protocol:

- Each message starts with a "Content-Length: N" header
- A blank line follows the header
- The JSON payload follows, with exact length N bytes

**Important:** Wait for the initialization response before sending commands.

### Commands

#### 1. Initialization

When the server starts, it automatically sends an initialization response:

```json
{
  "status": "initialized",
  "files_indexed": 420, 
  "project_path": "/absolute/path/to/project"
}
```

Wait for this message before sending any commands.

#### 2. Search

Request:
```json
{
  "command": "search",
  "pattern": "text to search for",
  "max_results": 100
}
```

- Use `r:pattern` prefix for raw regex patterns
- Regular patterns are automatically escaped

Response:
```json
{
  "status": "success",
  "total_matches": 42,
  "returned_matches": 20,
  "matches": [
    {
      "file": "src/example.py",
      "matches": [
        {
          "start": 120,
          "end": 127,
          "line": 25,
          "context": "...surrounding text with match..."
        }
      ]
    }
  ]
}
```

#### 3. Apply Changes

Request:
```json
{
  "command": "apply_changes",
  "changes": "```path/to/file.py\n<<<<<<< SEARCH\nold code\n=======\nnew code\n>>>>>>> REPLACE\n```"
}
```

The `changes` format:
- Wrapped in code blocks with file path as first line
- Each change has SEARCH and REPLACE sections
- Multiple changes can be specified in a single request

Response:
```json
{
  "status": "success",
  "message": "Changes applied"
}
```

#### 4. Shutdown

Request:
```json
{
  "command": "shutdown"
}
```

Response:
```json
{
  "status": "shutdown"
}
```

### Error Responses

All commands may return an error:
```json
{
  "error": "Error message details"
}
```

### Examples

Example search request:
```
Content-Length: 54

{"command":"search","pattern":"myFunction","max_results":10}
```

Example response:
```
Content-Length: 248

{"status":"success","total_matches":2,"returned_matches":2,"matches":[{"file":"src/app.js","matches":[{"start":120,"end":130,"line":25,"context":"function myFunction() { return true; }"}]}]}
```
