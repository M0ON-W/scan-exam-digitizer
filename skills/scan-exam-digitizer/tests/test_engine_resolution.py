from __future__ import annotations

import unittest

from helpers import portable_tectonic


class EngineResolutionTests(unittest.TestCase):
    def test_portable_tectonic_resolves_the_installed_windows_engine(self) -> None:
        engine = portable_tectonic()
        self.assertTrue(engine.is_file(), f"Tectonic path does not exist: {engine}")


if __name__ == "__main__":
    unittest.main()
