import json
import logging
import subprocess
from typing import Optional
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


def index_api_file(path: Path):
    logger.info(f"Starting to index API file: {path}")
    line_count = 0

    with open(path, "r") as f:
        for line in f:
            if line:
                line_count += 1
                ctag_entry = json.loads(line)
                if ctag_entry.get("kind") in ["function", "prototype"]:
                    function_name = ctag_entry.get("name", "")
                    signature = ctag_entry.get("signature", "")
                    return_type = ctag_entry.get("typeref", "").replace("typename:", "")
                    function_info = {
                        "name": function_name,
                        "signature": signature,
                        "return_type": return_type
                    }
                    DECLARATIONS.append(function_info)
                    WORD_INDEX[function_name].append(len(DECLARATIONS) - 1)

    INDEXED_APIS.append(path.stem)
    logger.info(f"Indexing complete for {path}. Processed {line_count} API entries")


def index_apis(apis_dir: Path):
    logger.info(f"Starting to index APIs from directory: {apis_dir}")

    if not apis_dir.exists():
        logger.error(f"APIs directory does not exist: {apis_dir}")
        return

    api_files = list(apis_dir.glob("*.ctags"))
    if not api_files:
        logger.warning(f"No .ctags files found in {apis_dir}")
        return

    for api_file in api_files:
        index_api_file(api_file)

    logger.info(f"Indexing complete. Total words indexed: {len(WORD_INDEX)}")
    logger.info(f"Total declarations: {len(DECLARATIONS)}")


def lookup(query: str) -> Optional[dict]:
    logger.info(f"Searching for query: '{query}'")

    if query in WORD_INDEX:
        declaration_indices = WORD_INDEX[query]
        if declaration_indices:
            function_info = DECLARATIONS[declaration_indices[0]]
            logger.info(f"Match found: '{function_info}'")
            return function_info

    logger.info("No match found")
    return None


@SERVER.tool()
def search_api(function_name: str) -> dict:
    """
    Search for API function declarations by function name.

    This tool searches through indexed API documentation to find function
    declarations that match the given function name and returns the function
    information including name, signature, and return type.

    Args:
        function_name: The name of the function to search for

    Returns:
        A dictionary containing function info (name, signature, return_type) if found,
        or error message if no match exists.
    """
    logger.info(f"API search requested for: '{function_name}'")
    result = lookup(function_name)
    if result:
        logger.info(f"Returning result: '{result}'")
        return result
    else:
        logger.info("No matches found for function_name")
        return {"error": "No matches found"}


@SERVER.tool()
def list_indexed_apis() -> dict:
    """
    List all currently indexed API files.

    Returns a list of API files that have been indexed and are available for searching.

    Returns:
        A dictionary containing the list of indexed API file names.
    """
    logger.info("Listing indexed APIs requested")

    if not INDEXED_APIS:
        return {"indexed_apis": [], "message": "No API files have been indexed yet."}

    return {"indexed_apis": INDEXED_APIS, "count": len(INDEXED_APIS)}


@SERVER.tool()
def generate_ctags(include_directory: str, ctags_filename: str) -> dict:
    """
    Generate ctags files for function signature lookup.

    This tool recursively generates ctags from C/C++ header files in the specified
    directory and all its subdirectories, then saves them to the apis directory
    for indexing by the MCP server.

    Args:
        include_directory: Path to the directory containing C/C++ header files
        ctags_filename: Name for the output ctags file (without extension)

    Returns:
        Dictionary with success status and details, or error information
    """
    logger.info(f"Generate ctags requested for directory: '{include_directory}', filename: '{ctags_filename}'")

    include_path = Path(include_directory)
    if not include_path.exists():
        error_msg = f"Include directory '{include_directory}' does not exist"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    if not include_path.is_dir():
        error_msg = f"'{include_directory}' is not a directory"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    apis_dir = Path("apis")

    output_file = apis_dir / f"{ctags_filename}.ctags"

    try:
        cmd = [
            "ctags",
            "--output-format=json",
            "--fields=+Sf",
            "--kinds-C=+p",
            "-R",
            "-f", str(output_file),
            str(include_path)
        ]

        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            index_api_file(output_file)
            logger.info(f"ctags generation and indexing complete: {output_file}")
            return {
                "success": True,
                "output_file": str(output_file),
                "message": "ctags generation and indexing complete"
            }
        else:
            logger.error(f"ctags failed with return code {result.returncode}")
            if result.stderr:
                logger.error(f"ctags stderr: {result.stderr}")
            if result.stdout:
                logger.error(f"ctags stdout: {result.stdout}")
            return {
                "success": False,
                "error": "ctags generation failed",
                "message": "Check the server log file for details"
            }

    except FileNotFoundError:
        error_msg = "ctags command not found. Please install Universal Ctags (e.g., 'brew install universal-ctags' on macOS)"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}


if __name__ == "__main__":
    logger.info("Starting API Lookup MCP Server")
    index_apis(Path("apis"))
    logger.info("Starting FastMCP server...")
    SERVER.run(transport="stdio")
