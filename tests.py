import tempfile
import unittest
from pathlib import Path
from main import (
    index_api_file,
    index_apis,
    lookup,
    WORD_INDEX,
    DECLARATIONS,
    extract_words,
)


class TestApiLookUpMCPServer(unittest.TestCase):

    def setUp(self):
        WORD_INDEX.clear()
        DECLARATIONS.clear()

    def test_extract_words(self):
        """Test that declarations are correctly split into words"""
        declaration = "bool SDL_Init(SDL_InitFlags flags);"
        words = extract_words(declaration)
        expected_words = ["bool", "sdl_init", "sdl_initflags", "flags"]
        self.assertEqual(words, expected_words)

    def test_lookup_no_match(self):
        result = lookup("NonExistentFunction")
        self.assertIsNone(result)

    def test_integration_index_and_lookup(self):
        sample_data = """bool SDL_Init(SDL_InitFlags flags);
                        void SDL_Quit(void);
                        SDL_Window *SDL_CreateWindow(const char *title, int w, int h, SDL_WindowFlags flags);
                        void SDL_DestroyWindow(SDL_Window *window);"""

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(sample_data)
            temp_path = Path(f.name)

        try:
            index_api_file(temp_path)
            result = lookup("sdl_init")
            self.assertEqual(result, "bool SDL_Init(SDL_InitFlags flags);")
            result = lookup("sdl_quit")
            self.assertEqual(result, "void SDL_Quit(void);")
            result = lookup("sdl_nonexistentfunction")
            self.assertIsNone(result)

        finally:
            temp_path.unlink()

    def test_index_apis_directory(self):
        """Test that multiple API files are loaded from a directory"""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            api1_content = """bool SDL_Init(SDL_InitFlags flags);
                                void SDL_Quit(void);"""
            (temp_path / "sdl_core.api").write_text(api1_content)

            api2_content = """SDL_Window *SDL_CreateWindow(const char *title, int w, int h, SDL_WindowFlags flags);
                        void SDL_DestroyWindow(SDL_Window *window);"""
            (temp_path / "sdl_window.api").write_text(api2_content)

            index_apis(temp_path)

            result = lookup("sdl_init")
            self.assertEqual(result, "bool SDL_Init(SDL_InitFlags flags);")

            result = lookup("sdl_createwindow")
            self.assertEqual(
                result,
                "SDL_Window *SDL_CreateWindow(const char *title, int w, int h, SDL_WindowFlags flags);",
            )

            result = lookup("sdl_destroywindow")
            self.assertEqual(result, "void SDL_DestroyWindow(SDL_Window *window);")


if __name__ == "__main__":
    unittest.main()
