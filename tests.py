import tempfile
import unittest
import os
from pathlib import Path
from main import lookup, generate_ctags, init_database, search_declarations, list_indexed_apis, list_api_files, list_functions_by_file


class TestApiLookUpMCPServer(unittest.TestCase):

    def test_generate_ctags_integration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            os.chdir(temp_dir)

            init_database()

            apis_dir = temp_path / "apis"
            apis_dir.mkdir()

            header1_content = """
                            int add_numbers(int a, int b);
                            int subtract_numbers(int a, int b);
                            int multiply_numbers(int a, int b);
                            float divide_numbers(float a, float b);
                            void print_result(int result);
            """
            header1_file = temp_path / "math.h"
            header1_file.write_text(header1_content)

            header2_content = """
                            char* get_string(void);
                            int string_length(const char* str);
                            void clear_buffer(void);
            """
            header2_file = temp_path / "string_utils.h"
            header2_file.write_text(header2_content)

            try:
                result = generate_ctags(str(temp_path))

                self.assertIsInstance(result, dict)
                self.assertTrue(result.get("success", False))
                self.assertIn("message", result)
                self.assertEqual(
                    result["message"], "ctags generation and indexing complete")

                add_result = lookup("add_numbers")
                self.assertIsNotNone(add_result)
                self.assertIsInstance(add_result, list)
                self.assertEqual(len(add_result), 1)
                self.assertEqual(add_result[0]["name"], "add_numbers")

                search_result = search_declarations("add_numbers")
                self.assertIsInstance(search_result, dict)
                self.assertIn("matches", search_result)
                self.assertIn("count", search_result)
                self.assertEqual(search_result["count"], 1)
                self.assertEqual(len(search_result["matches"]), 1)
                self.assertEqual(
                    search_result["matches"][0]["name"], "add_numbers")

                list_result = list_indexed_apis()
                self.assertIsInstance(list_result, dict)
                self.assertIn("indexed_apis", list_result)
                self.assertIn("count", list_result)
                self.assertEqual(list_result["count"], 1)
                self.assertEqual(len(list_result["indexed_apis"]), 1)
                self.assertEqual(
                    list_result["indexed_apis"][0], temp_path.name)

                nonexistent_search = search_declarations("nonexistent_function")
                self.assertIsInstance(nonexistent_search, dict)
                self.assertEqual(nonexistent_search["count"], 0)
                self.assertEqual(len(nonexistent_search["matches"]), 0)

                files_result = list_api_files(temp_path.name)
                self.assertIsInstance(files_result, dict)
                self.assertIn("api_name", files_result)
                self.assertIn("files", files_result)
                self.assertIn("count", files_result)
                self.assertEqual(files_result["api_name"], temp_path.name)
                self.assertEqual(files_result["count"], 2)
                self.assertEqual(len(files_result["files"]), 2)

                self.assertIn(f"{temp_path.name}/math.h",
                              files_result["files"])
                self.assertIn(f"{temp_path.name}/string_utils.h",
                              files_result["files"])

                empty_files_result = list_api_files("nonexistent_api")
                self.assertIsInstance(empty_files_result, dict)
                self.assertEqual(empty_files_result["count"], 0)
                self.assertEqual(len(empty_files_result["files"]), 0)

                math_file = [f for f in files_result["files"]
                             if "math.h" in f][0]
                functions_result = list_functions_by_file(math_file)
                self.assertIsInstance(functions_result, dict)
                self.assertIn("functions", functions_result)
                self.assertIn("count", functions_result)

                self.assertEqual(functions_result["count"], 5)
                self.assertEqual(len(functions_result["functions"]), 5)
                self.assertIn("add_numbers", functions_result["functions"])

                files_paginated = list_api_files(
                    temp_path.name, offset=0, limit=1)
                self.assertIsInstance(files_paginated, dict)
                self.assertIn("offset", files_paginated)
                self.assertIn("limit", files_paginated)
                self.assertEqual(files_paginated["count"], 1)
                self.assertEqual(files_paginated["offset"], 0)
                self.assertEqual(files_paginated["limit"], 1)

                files_offset = list_api_files(
                    temp_path.name, offset=1, limit=1)
                self.assertEqual(files_offset["count"], 1)
                self.assertEqual(files_offset["offset"], 1)

                all_files = list_api_files(temp_path.name)
                math_file = [f for f in all_files["files"] if "math.h" in f][0]

                functions_limited = list_functions_by_file(
                    math_file, offset=0, limit=2)
                self.assertIsInstance(functions_limited, dict)
                self.assertIn("offset", functions_limited)
                self.assertIn("limit", functions_limited)
                self.assertEqual(functions_limited["count"], 2)
                self.assertEqual(functions_limited["offset"], 0)
                self.assertEqual(functions_limited["limit"], 2)

                functions_offset = list_functions_by_file(
                    math_file, offset=2, limit=3)
                self.assertEqual(functions_offset["count"], 3)
                self.assertEqual(functions_offset["offset"], 2)
                self.assertEqual(functions_offset["limit"], 3)

                empty_functions_result = list_functions_by_file(
                    "nonexistent.h")
                self.assertIsInstance(empty_functions_result, dict)
                self.assertEqual(empty_functions_result["count"], 0)
                self.assertEqual(len(empty_functions_result["functions"]), 0)

            except Exception as e:
                self.fail(f"generate_ctags raised an exception: {str(e)}")
            finally:
                os.chdir(Path(__file__).parent)

    def test_gitignore_integration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            os.chdir(temp_dir)

            init_database()

            apis_dir = temp_path / "apis"
            apis_dir.mkdir()

            gitignore_content = """venv
                                    *.log
                                    __pycache__"""
            gitignore_file = temp_path / ".gitignore"
            gitignore_file.write_text(gitignore_content)

            header_content = "int main_function(void);"
            header_file = temp_path / "main.h"
            header_file.write_text(header_content)

            venv_dir = temp_path / "venv"
            venv_dir.mkdir()
            venv_header = venv_dir / "venv_function.h"
            venv_header.write_text("int venv_function(void);")

            log_file = temp_path / "debug.log"
            log_file.write_text("log content")

            pycache_dir = temp_path / "__pycache__"
            pycache_dir.mkdir()

            try:
                result = generate_ctags(str(temp_path))

                self.assertTrue(result.get("success", False))

                main_result = lookup("main_function")
                self.assertIsNotNone(main_result)
                self.assertEqual(len(main_result), 1)

                venv_result = lookup("venv_function")
                self.assertIsNone(venv_result)

            except Exception as e:
                self.fail(f"gitignore integration test failed: {str(e)}")
            finally:
                os.chdir(Path(__file__).parent)


if __name__ == "__main__":
    unittest.main()
