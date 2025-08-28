import tempfile
import unittest
from pathlib import Path
from main import (
    lookup,
    WORD_INDEX,
    DECLARATIONS,
    INDEXED_APIS,
    generate_ctags,
)


class TestApiLookUpMCPServer(unittest.TestCase):

    def setUp(self):
        WORD_INDEX.clear()
        DECLARATIONS.clear()
        INDEXED_APIS.clear()


    def test_generate_ctags_integration(self):
        """Test that ctags generation works with a real header file"""

        ctags_file = Path("apis/test_header.ctags")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            header_content = "int add_numbers(int a, int b);"
            header_file = temp_path / "test.h"
            header_file.write_text(header_content)

            try:
                result = generate_ctags(str(temp_path), "test_header")

                self.assertIsInstance(result, dict)
                self.assertTrue(result.get("success", False))
                self.assertIn("message", result)
                self.assertEqual(result["message"], "ctags generation and indexing complete")

                add_result = lookup("add_numbers")
                self.assertIsNotNone(add_result)
                self.assertIsInstance(add_result, dict)
                self.assertEqual(add_result["name"], "add_numbers")

            except Exception as e:
                self.fail(f"generate_ctags raised an exception: {str(e)}")
            finally:
                # Clean up the created ctags file
                if ctags_file.exists():
                    ctags_file.unlink()


if __name__ == "__main__":
    unittest.main()
