# Function Signature Lookup MCP Server

An MCP server that provides function signature lookups for any API. Comes with SDL3 API as an example.

## Installation

```bash
git clone git@github.com:osinmv/function-lookup-mcp.git
cd function-lookup-mcp
claude mcp add api-lookup $(pwd)/run.sh -s user
```

## Usage

**`search_api(function_name: str)`** - Look up function signatures

Example:
```
search_api("SDL_Init")
→ "bool SDL_Init(SDL_InitFlags flags);"
```

**`list_indexed_apis()`** - List all indexed API files

Example:
```
list_indexed_apis()
→ "Indexed API files: sdl3"
```

## Extending the Index

Drop a `.api` file with function declarations in the `apis/` folder and restart the MCP server to update the index.