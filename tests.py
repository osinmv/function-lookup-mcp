import tempfile
import unittest
import os
from pathlib import Path
from main import lookup, generate_ctags, init_database, search_api, list_indexed_apis, list_api_files, list_functions_by_file


class TestApiLookUpMCPServer(unittest.TestCase):

    def test_generate_ctags_integration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            os.chdir(temp_dir)

            init_database()

            apis_dir = temp_path / "apis"
            apis_dir.mkdir()

            header_content = "int add_numbers(int a, int b);"
            header_file = temp_path / "test.h"
            header_file.write_text(header_content)

            try:
                result = generate_ctags(str(temp_path), "test_header")

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

                search_result = search_api("add_numbers")
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
                self.assertEqual(list_result["indexed_apis"][0], "test_header")

                nonexistent_search = search_api("nonexistent_function")
                self.assertIsInstance(nonexistent_search, dict)
                self.assertEqual(nonexistent_search["count"], 0)
                self.assertEqual(len(nonexistent_search["matches"]), 0)

                files_result = list_api_files("test_header")
                self.assertIsInstance(files_result, dict)
                self.assertIn("api_name", files_result)
                self.assertIn("files", files_result)
                self.assertIn("count", files_result)
                self.assertEqual(files_result["api_name"], "test_header")
                self.assertEqual(files_result["count"], 1)
                self.assertEqual(len(files_result["files"]), 1)
                self.assertIn("test.h", files_result["files"][0])

                empty_files_result = list_api_files("nonexistent_api")
                self.assertIsInstance(empty_files_result, dict)
                self.assertEqual(empty_files_result["count"], 0)
                self.assertEqual(len(empty_files_result["files"]), 0)

                file_path = files_result["files"][0]
                functions_result = list_functions_by_file(
                    file_path, "test_header")
                self.assertIsInstance(functions_result, dict)
                self.assertIn("functions", functions_result)
                self.assertIn("count", functions_result)
                self.assertEqual(functions_result["count"], 1)
                self.assertEqual(len(functions_result["functions"]), 1)
                self.assertEqual(
                    functions_result["functions"][0], "add_numbers")

                empty_functions_result = list_functions_by_file(
                    "nonexistent.h", "test_header")
                self.assertIsInstance(empty_functions_result, dict)
                self.assertEqual(empty_functions_result["count"], 0)
                self.assertEqual(len(empty_functions_result["functions"]), 0)

            except Exception as e:
                self.fail(f"generate_ctags raised an exception: {str(e)}")
            finally:
                os.chdir(Path(__file__).parent)


if __name__ == "__main__":
    unittest.main()
