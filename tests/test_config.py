from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from eightbit_buddy.config import config_template, load_config, write_config


class ConfigTests(unittest.TestCase):
    def test_round_trip_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            write_config(path, config_template("192.0.2.10"))
            config = load_config(path)
            self.assertEqual(config.display.driver, "awtrix")
            self.assertEqual(config.display.host, "192.0.2.10")
            self.assertTrue(config.server.token)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_existing_config_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            write_config(path, config_template("display.local"))
            with self.assertRaises(FileExistsError):
                write_config(path, config_template("other.local"))


if __name__ == "__main__":
    unittest.main()
