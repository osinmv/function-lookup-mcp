import logging
import re
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("api-lookup-mcp-server.log")],
)
logger = logging.getLogger(__name__)

SERVER = FastMCP("api-lookup")
WORD_INDEX = defaultdict(list)
DECLARATIONS = []
INDEXED_APIS = []


def extract_words(line: str) -> list[str]:
    words = re.findall(r"\b\w+\b", line.lower())
    return words


def index_api_file(path: Path):
    logger.info(f"Starting to index API file: {path}")
    line_count = 0

    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                line_count += 1
                DECLARATIONS.append(line)
                declaration_idx = len(DECLARATIONS) - 1

                words = extract_words(line)
                for word in words:
                    WORD_INDEX[word].append(declaration_idx)

    INDEXED_APIS.append(path.stem)
    logger.info(f"Indexing complete for {path}. Processed {line_count} API entries")


def index_apis(apis_dir: Path):
    logger.info(f"Starting to index APIs from directory: {apis_dir}")

    if not apis_dir.exists():
        logger.error(f"APIs directory does not exist: {apis_dir}")
        return

    api_files = list(apis_dir.glob("*.api"))
    if not api_files:
        logger.warning(f"No .api files found in {apis_dir}")
        return

    for api_file in api_files:
        index_api_file(api_file)

    logger.info(f"Indexing complete. Total words indexed: {len(WORD_INDEX)}")
    logger.info(f"Total declarations: {len(DECLARATIONS)}")


def lookup(query: str):
    logger.info(f"Searching for query: '{query}'")
    query_lower = query.lower()

    if query_lower in WORD_INDEX:
        declaration_indices = WORD_INDEX[query_lower]
        if declaration_indices:
            result = DECLARATIONS[declaration_indices[0]]
            logger.info(f"Match found: '{result}'")
            return result

    logger.info("No match found")
    return None


@SERVER.tool()
def search_api(function_name: str) -> str:
    """
    Search for API function declarations by function name.
    
    This tool searches through indexed API documentation to find function 
    declarations that match the given function name and returns the complete 
    function signature if found.
    
    Args:
        function_name: The name of the function to search for
    
    Returns:
        The complete function declaration if found, or "No matches found" if no match exists.
    """
    logger.info(f"API search requested for: '{function_name}'")
    result = lookup(function_name)
    if result:
        logger.info(f"Returning result: '{result}'")
        return result
    else:
        logger.info("No matches found for function_name")
        return "No matches found"


@SERVER.tool()
def list_indexed_apis() -> str:
    """
    List all currently indexed API files.
    
    Returns a list of API files that have been indexed and are available for searching.
    
    Returns:
        A comma-separated list of indexed API file names.
    """
    logger.info("Listing indexed APIs requested")
    
    if not INDEXED_APIS:
        return "No API files have been indexed yet."
    
    return f"Indexed API files: {', '.join(INDEXED_APIS)}"


if __name__ == "__main__":
    logger.info("Starting API Lookup MCP Server")
    index_apis(Path("apis"))
    logger.info("Starting FastMCP server...")
    SERVER.run(transport="stdio")
