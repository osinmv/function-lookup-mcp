import json
import hashlib
import logging
import sqlite3
import subprocess
import fnmatch
import os
from typing import Optional, Set
from pathlib import Path
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(
        "api-lookup-mcp-server.log")],
)
logger = logging.getLogger(__name__)

SERVER = FastMCP("api-lookup")
DB_PATH = "ctags_index.db"


def get_db_connection(db_path=None):
    """Get a database connection. Use provided path or default."""
    path = db_path or DB_PATH
    return sqlite3.connect(path)


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    hash_sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_stored_file_hash(api_name: str, db_path=None) -> Optional[str]:
    """Get the stored hash for an API file."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT file_hash FROM indexed_apis WHERE api_name = ?", (api_name,))
        result = cursor.fetchone()
        return result[0] if result else None


def update_file_hash(api_name: str, file_hash: str, db_path=None, conn=None):
    """Update the stored hash for an API file."""
    if conn is None:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO indexed_apis (api_name, file_hash) VALUES (?, ?)
            """, (api_name, file_hash))
            conn.commit()
    else:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO indexed_apis (api_name, file_hash) VALUES (?, ?)
        """, (api_name, file_hash))


def check_fts5_support() -> bool:
    """Check if SQLite has FTS5 support enabled."""
    try:
        with get_db_connection(":memory:") as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE VIRTUAL TABLE test_fts USING fts5(content)")
            cursor.execute("DROP TABLE test_fts")
            return True
    except sqlite3.OperationalError as e:
        logger.error(f"FTS5 support check failed: {e}")
        return False


def init_database(db_path=None):
    """Initialize the SQLite database with comprehensive ctags schema."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ctags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                name TEXT NOT NULL,
                input_file TEXT,
                pattern TEXT,
                kind TEXT,
                line INTEGER,
                
                signature TEXT,
                typeref TEXT,
                scope TEXT,
                file_restricted BOOLEAN DEFAULT FALSE,
                
                class TEXT,
                struct TEXT,
                union_name TEXT,
                enum TEXT,
                access TEXT,
                implementation TEXT,
                inherits TEXT,
                
                extensions TEXT,
                
                raw_data TEXT,
                
                api_file TEXT NOT NULL,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_name ON ctags(name)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_kind ON ctags(kind)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_file ON ctags(api_file)
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS indexed_apis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_name TEXT UNIQUE NOT NULL,
                file_hash TEXT,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS ctags_fts USING fts5(
                raw_data,
                content='ctags',
                content_rowid='id'
            )
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS ctags_ai AFTER INSERT ON ctags BEGIN
                INSERT INTO ctags_fts(rowid, raw_data)
                VALUES (new.id, new.raw_data);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS ctags_ad AFTER DELETE ON ctags BEGIN
                INSERT INTO ctags_fts(ctags_fts, rowid, raw_data)
                VALUES('delete', old.id, old.raw_data);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS ctags_au AFTER UPDATE ON ctags BEGIN
                INSERT INTO ctags_fts(ctags_fts, rowid, raw_data)
                VALUES('delete', old.id, old.raw_data);
                INSERT INTO ctags_fts(rowid, raw_data)
                VALUES (new.id, new.raw_data);
            END
        """)

        conn.commit()


def clear_api_from_db(api_name: str, db_path=None):
    """Remove all entries for a specific API from the database."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM ctags WHERE api_file = ?", (api_name,))
        cursor.execute(
            "DELETE FROM indexed_apis WHERE api_name = ?", (api_name,))

        conn.commit()


def index_api_file(path: Path, db_path=None):
    logger.info(f"Starting to index API file: {path}")
    line_count = 0
    processed_count = 0
    api_name = path.stem

    clear_api_from_db(api_name, db_path)

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        with open(path, "r") as f:
            for line in f:
                if line.strip():
                    line_count += 1
                    try:
                        ctag_entry = json.loads(line)

                        if ctag_entry.get("_type") != "tag":
                            continue

                        processed_count += 1
                        name = ctag_entry.get("name", "")
                        input_file = Path(ctag_entry.get("path", ""))
                        input_file = "/".join(
                            input_file.parts[input_file.parts.index(api_name):])

                        pattern = ctag_entry.get("pattern", "")
                        kind = ctag_entry.get("kind", "")
                        line_num = ctag_entry.get("line")
                        signature = ctag_entry.get("signature", "")
                        typeref = ctag_entry.get("typeref", "")
                        scope = ctag_entry.get("scope", "")
                        file_restricted = ctag_entry.get("file", False)

                        class_name = ctag_entry.get("class", "")
                        struct_name = ctag_entry.get("struct", "")
                        union_name = ctag_entry.get("union", "")
                        enum_name = ctag_entry.get("enum", "")
                        access = ctag_entry.get("access", "")
                        implementation = ctag_entry.get("implementation", "")
                        inherits = ctag_entry.get("inherits", "")

                        raw_data = line.strip()

                        cursor.execute("""
                            INSERT INTO ctags (
                                name, input_file, pattern, kind, line,
                                signature, typeref, scope, file_restricted,
                                class, struct, union_name, enum, access, implementation, inherits,
                                extensions, api_file, raw_data
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            name, input_file, pattern, kind, line_num,
                            signature, typeref, scope, file_restricted,
                            class_name, struct_name, union_name, enum_name,
                            access, implementation, inherits,
                            None, api_name, raw_data
                        ))

                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"Failed to parse JSON line {line_count}: {e}")
                        continue

        update_file_hash(api_name, calculate_file_hash(path), db_path, conn)

        conn.commit()

    logger.info(
        f"Indexing complete for {path}. Processed {processed_count} tag entries out of {line_count} total entries")


def index_apis(apis_dir: Path, db_path=None):
    logger.info(f"Starting to index APIs from directory: {apis_dir}")

    if not apis_dir.exists():
        logger.error(f"APIs directory does not exist: {apis_dir}")
        return

    api_files = list(apis_dir.glob("*.ctags"))
    if not api_files:
        logger.warning(f"No .ctags files found in {apis_dir}")
        return

    files_to_index = []
    files_skipped = 0

    for api_file in api_files:
        api_name = api_file.stem
        current_hash = calculate_file_hash(api_file)
        stored_hash = get_stored_file_hash(api_name, db_path)

        if stored_hash == current_hash:
            logger.info(f"Skipping {api_file.name} - no changes detected")
            files_skipped += 1
        else:
            logger.info(f"File {api_file.name} has changed - will reindex")
            files_to_index.append(api_file)

    if files_to_index:
        logger.info(
            f"Indexing {len(files_to_index)} changed files (skipped {files_skipped})")
        for api_file in files_to_index:
            index_api_file(api_file, db_path)
    else:
        logger.info(
            f"All {len(api_files)} API files are up to date - no indexing needed")

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ctags")
        total_entries = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT name) FROM ctags")
        unique_names = cursor.fetchone()[0]

    logger.info(f"Indexing complete. Total entries: {total_entries}")
    logger.info(f"Unique function names: {unique_names}")


def lookup(query: str, db_path=None) -> Optional[list]:
    logger.info(f"Searching for query: '{query}'")

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, signature, typeref 
            FROM ctags 
            WHERE name = ?
        """, (query,))

        rows = cursor.fetchall()

        if rows:
            matches = []
            for row in rows:
                name, signature, typeref = row
                match_info = {
                    "name": name,
                    "signature": signature or "",
                    "return_type": typeref.replace("typename:", "") if typeref else ""
                }
                matches.append(match_info)

            logger.info(f"Found {len(matches)} matches for '{query}'")
            return matches

    logger.info("No match found")
    return None


@SERVER.tool()
def search_declarations(name: str, offset: int = 0, limit: int = 10) -> dict:
    """
    Search for code declarations by name.

    Returns definitions, declarations, and mentions of the given name.

    Args:
        name: Name to search for
        offset: Number of results to skip (default: 0)
        limit: Maximum results (default: 10)

    Returns:
        Dictionary with matches and count.
    """
    logger.info(f"Declaration search requested for: '{name}' (offset={offset}, limit={limit})")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.name, c.kind, c.signature, c.typeref, c.input_file, c.line,
                   c.scope, c.class, c.struct, c.union_name, c.enum, c.api_file, c.raw_data
            FROM ctags c
            INNER JOIN ctags_fts fts ON c.id = fts.rowid
            WHERE ctags_fts MATCH ?
            LIMIT ? OFFSET ?
        """, (name, limit, offset))

        rows = cursor.fetchall()

        if rows:
            matches = []
            for row in rows:
                elem_name, elem_kind, signature, typeref, file_path, line, scope, class_name, struct_name, union_name, enum_name, api_file, raw_data = row

                match_info = {
                    "name": elem_name,
                    "kind": elem_kind,
                    "signature": signature or "",
                    "return_type": typeref.replace("typename:", "") if typeref else "",
                    "file": file_path or "",
                    "line": line or 0,
                    "api": api_file,
                    "scope": scope or "",
                    "class": class_name or "",
                    "struct": struct_name or "",
                    "union": union_name or "",
                    "enum": enum_name or "",
                    "definition": raw_data or ""
                }
                matches.append(match_info)

            logger.info(f"Found {len(matches)} matches for '{name}'")
            return {
                "matches": matches,
                "count": len(matches),
                "offset": offset,
                "limit": limit
            }

    logger.info("No matches found")
    return {
        "matches": [],
        "count": 0,
        "offset": offset,
        "limit": limit
    }


@SERVER.tool()
def list_indexed_apis() -> dict:
    """
    List all currently indexed API files.

    Returns a list of API files that have been indexed and are available for searching.

    Returns:
        A dictionary containing the list of indexed API file names.
    """
    logger.info("Listing indexed APIs requested")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT api_name FROM indexed_apis ORDER BY indexed_at")
        rows = cursor.fetchall()

        if not rows:
            return {"indexed_apis": [], "message": "No API files have been indexed yet."}

        api_names = [row[0] for row in rows]
        return {"indexed_apis": api_names, "count": len(api_names)}


@SERVER.tool()
def list_api_files(api_name: str, offset: int = 0, limit: int = 100) -> dict:
    """
    Extract a list of files/paths for a given API.

    This tool returns all unique file paths that are indexed for the specified API,
    showing which files contain functions for that API.

    Args:
        api_name: The name of the API to get file paths for
        offset: Number of files to skip (for pagination)
        limit: Maximum number of files to return (default: 100)

    Returns:
        A dictionary containing the list of file paths and pagination info.
    """
    logger.info(
        f"Listing files for API: '{api_name}' (offset={offset}, limit={limit})")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT input_file 
            FROM ctags 
            WHERE api_file = ? AND input_file IS NOT NULL AND input_file != ''
            ORDER BY input_file
            LIMIT ? OFFSET ?
        """, (api_name, limit, offset))

        rows = cursor.fetchall()
        file_paths = [row[0] for row in rows] if rows else []

        logger.info(f"Found {len(file_paths)} files for API '{api_name}'")
        return {
            "api_name": api_name,
            "files": file_paths,
            "count": len(file_paths),
            "offset": offset,
            "limit": limit
        }


@SERVER.tool()
def list_functions_by_file(file_path: str, offset: int = 0, limit: int = 100) -> dict:
    """
    Extract all functions from a given file/path.

    This tool returns all functions found in the specified file path.

    Args:
        file_path: The file path to get functions for
        offset: Number of functions to skip (for pagination)
        limit: Maximum number of functions to return (default: 100)

    Returns:
        A dictionary containing functions found in the specified file and pagination info.
    """
    logger.info(
        f"Listing functions for file: '{file_path}' (offset={offset}, limit={limit})")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name
            FROM ctags 
            WHERE input_file = ? AND ( kind = 'function' OR kind = 'prototype' OR kind = 'func')
            ORDER BY line
            LIMIT ? OFFSET ?
        """, (file_path, limit, offset))

        rows = cursor.fetchall()
        functions = [row[0] for row in rows] if rows else []

        logger.info(f"Found {len(functions)} functions in file '{file_path}'")
        return {
            "functions": functions,
            "count": len(functions),
            "offset": offset,
            "limit": limit
        }


def get_gitignore_excludes(directory: Path) -> Set[str]:
    gitignore_path = directory / '.gitignore'
    excludes = set()

    if not gitignore_path.exists():
        return excludes

    patterns = []
    try:
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
    except Exception as e:
        logger.warning(f"Failed to read .gitignore: {e}")
        return excludes

    for item in os.listdir(directory):
        item_path = directory / item
        for pattern in patterns:
            if fnmatch.fnmatch(item, pattern):
                excludes.add(str(item_path))
                break

    return excludes


@SERVER.tool()
def generate_ctags(include_directory: str) -> dict:
    """
    Generate ctags files for function signature lookup.

    This tool recursively generates ctags from source files in the specified
    directory and all its subdirectories, then saves them to the apis directory
    for indexing by the MCP server.

    Args:
        include_directory: Path to the directory containing source files

    Returns:
        Dictionary with success status and details, or error information
    """
    include_path = Path(include_directory)

    logger.info(
        f"Generate ctags requested for directory: '{include_directory}', filename: '{include_path.name}'")

    if not include_path.exists():
        error_msg = f"Include directory '{include_directory}' does not exist"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    if not include_path.is_dir():
        error_msg = f"'{include_directory}' is not a directory"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    apis_dir = Path("apis")
    apis_dir.mkdir(exist_ok=True)

    output_file = apis_dir / f"{include_path.name}.ctags"

    try:
        cmd = [
            "ctags",
            "--output-format=json",
            "--fields=+Sf",
            "--kinds-C=+p",
            "-R",
            "-f", str(output_file),
        ]

        excludes = get_gitignore_excludes(include_path)
        for pattern in excludes:
            cmd.append(f"--exclude={pattern}")

        cmd.append(str(include_path))

        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            index_api_file(output_file)
            logger.info(
                f"ctags generation and indexing complete: {output_file}")
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
    try:
        logger.info("Starting API Lookup MCP Server")

        logger.info("Checking FTS5 support...")
        if not check_fts5_support():
            logger.error("FTS5 support is not available in your SQLite installation.")
            logger.error("Please ensure you have SQLite compiled with FTS5 enabled.")
            logger.error("MCP server cannot start without FTS5 support.")
            import sys
            sys.exit(1)
        logger.info("FTS5 support confirmed")

        logger.info("Initializing database...")
        init_database()
        logger.info("Database initialization complete")

        logger.info("Indexing APIs from 'apis' directory...")
        index_apis(Path("apis"))
        logger.info("API indexing complete")

        logger.info("Starting FastMCP server...")
        SERVER.run(transport="stdio")

    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}", exc_info=True)
        raise
