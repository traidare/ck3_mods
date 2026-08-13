from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from gen.__main__ import load_entrypoint


class EntrypointLoadingTest(unittest.TestCase):
    def test_relative_imports_are_available_only_during_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "helper.py").write_text("VALUE = 42\n", encoding="utf-8")
            entrypoint = root / "implementation.py"
            entrypoint.write_text(
                "def generate(_context):\n"
                "    from .helper import VALUE\n"
                "    return VALUE\n",
                encoding="utf-8",
            )
            before = set(sys.modules)
            with load_entrypoint(entrypoint, "generate") as generate:
                self.assertEqual(generate(None), 42)
            self.assertEqual(set(sys.modules), before)


if __name__ == "__main__":
    unittest.main()
