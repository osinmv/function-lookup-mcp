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

Just ask your coding agent to index your header folder. Alternatively, you can drop existing ctags files into the `apis/` folder and restart the MCP server to update the index.


## MCP functions

**`search_api(function_name: str)`** - Look up function signatures

**`list_indexed_apis()`** - List all indexed API files

**`generate_ctags(include_directory: str, ctags_filename: str)`** - Generate ctags from header files and add to index

