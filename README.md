# Function Signature Lookup MCP Server

An MCP server that provides function signature lookups for any API. Uses SQLite database and universal ctags to extract functions and prototypes for indexing source files. Supports all languages that ctags supports including Python, C, Go, C++, JavaScript, Rust, Java, and many others.

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

Just ask your coding agent to index your header folder. Alternatively, you can generate ctags files manually using universal ctags:

```bash
ctags --output-format=json --fields=+Sf --kinds-C=+p -R -f apis/your_api.ctags /path/to/your/headers
```

Or drop existing ctags files into the `apis/` folder and restart the MCP server to update the index.


## MCP functions

**`search_api(function_name: str)`** - Look up function signatures

**`list_indexed_apis()`** - List all indexed API files

**`list_api_files(api_name: str)`** - List all unique file paths for a specific API

**`list_functions_by_file(file_path: str)`** - List all functions found in a specific file

**`generate_ctags(include_directory: str)`** - Generate ctags from header files and add to index

