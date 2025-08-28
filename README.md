# Function Signature Lookup MCP Server

An MCP server that provides function signature lookups for any API. Uses universal ctags to extract functions and prototypes for indexing header files.

## Requirements

- Python 3.13
- Universal Ctags 6.2.0

## Installation

```bash
git clone git@github.com:osinmv/function-lookup-mcp.git
cd function-lookup-mcp
claude mcp add api-lookup $(pwd)/run.sh -s user
```

## Extending the Index

Use the `generate_ctags()` MCP tool to automatically extract function signatures from header files and add them to the index. Alternatively, you can drop existing ctags files into the `apis/` folder and restart the MCP server to update the index.


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
→ "Indexed API files: example_api"
```

**`generate_ctags(include_directory: str, ctags_filename: str)`** - Generate ctags from header files and add to index

Example:
```
generate_ctags("/usr/include/SDL3", "sdl3")
→ "Successfully generated ctags for SDL3 headers"
```
