# Code Declaration Lookup MCP Server

An MCP server that provides full text search for code declarations. Uses SQLite with FTS5 and universal ctags to index and search functions, classes, structures, enums, and other code elements. Supports all languages that ctags supports including Python, C, Go, C++, JavaScript, Rust, Java, and many others.

## Requirements

- Python 3.13
- Universal Ctags 6.2.0
- SQLite with FTS5 support (included in Python 3.13)

## Installation

```bash
git clone git@github.com:osinmv/function-lookup-mcp.git
cd function-lookup-mcp
claude mcp add api-lookup $(pwd)/run.sh -s user
```

## Extending the Index

Just ask your coding agent to index your header folder. The indexing process respects your project's `.gitignore` file to avoid indexing unwanted files. Alternatively, you can generate ctags files manually using universal ctags:

```bash
ctags --output-format=json --fields=+Sf --kinds-C=+p -R -f apis/your_api.ctags /path/to/your/headers
```

Or drop existing ctags files into the `apis/` folder and restart the MCP server to update the index.


## MCP functions

**`search_declarations(name: str, offset: int = 0, limit: int = 10)`** - Search for code declarations by name

**`list_indexed_apis()`** - List all indexed API files

**`list_api_files(api_name: str, offset: int = 0, limit: int = 100)`** - List all unique file paths for a specific API

**`list_functions_by_file(file_path: str, offset: int = 0, limit: int = 100)`** - List all functions found in a specific file

**`generate_ctags(include_directory: str)`** - Generate ctags from source files and add to index

