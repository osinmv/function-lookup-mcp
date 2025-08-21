# Function Signature Lookup MCP Server

An MCP server that provides function signature lookups for any API. Comes with SDL3 API as an example.

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Add to Claude Code MCP configuration:
```json
{
  "mcpServers": {
    "sdl3-lookup": {
      "command": "python",
      "args": ["path/to/main.py"]
    }
  }
}
```

## Usage

**`search_api(function_name: str)`** - Look up function signatures

Example:
```
search_api("SDL_Init")
→ "bool SDL_Init(SDL_InitFlags flags);"
```